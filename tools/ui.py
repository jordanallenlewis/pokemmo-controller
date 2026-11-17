"""The remap screen: change what each controller input does, in your browser.

    python tools/setup.py --ui          (the installers pass --ui on to this)

It starts a small web page on this computer only (127.0.0.1, a random port, a
one-time key in the address), opens it in your default browser and stops when
you close the tab or press Quit. Nothing is sent anywhere and nothing needs
installing: it is part of this project and uses only what Python ships with.

The page edits a layout (see layout.py). "Apply" hands the layout to
setup.py --layout, the same code that installs the default, with the same
backup, atomic writes and exact uninstall. PokeMMO must be closed to apply.
PokeMMO's rule, one input = one action, is enforced in layout.py: the page
cannot ask for anything else, and neither can a request sent by hand.
"""
import http.server, json, os, secrets, subprocess, sys, tempfile, threading, webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_native  # noqa: E402
import layout as L  # noqa: E402
import pads  # noqa: E402
import platforms as P  # noqa: E402
from common import STATE_NAME, VERSION  # noqa: E402

HERE = Path(__file__).resolve().parent
PAGE = HERE / "ui_page.html"
MAX_BODY = L.MAX_BYTES + 1024

# The axes a bind may use (the right stick, 2 and 3, belongs to the wheel).
BIND_AXES = [n for n in range(L.AXES) if n not in L.RIGHT_STICK]


def _record(pokemmo):
    try:
        rec = json.loads((Path(pokemmo) / "config" / STATE_NAME).read_text(encoding="utf-8"))
        return rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        return {}


def saved_layout(pokemmo):
    """The layout in the install record, or the default."""
    lay = _record(pokemmo).get("layout")
    if lay:
        try:
            return L.recorded(lay)[0], True
        except L.LayoutError:
            pass
    return L.default_layout(), False


def pad_names(switch_positional):
    """{family: {title, buttons, axes}}: what each layout input is printed as on that pad.
    On Switch Pro the names follow the installed setting (see pads.py)."""
    out = {}
    for fam in pads.FAMILIES:
        axes = []
        for n in BIND_AXES:
            if n in (0, 1):   # a stick axis: one entry per direction
                axes += [{"n": n, "positive": pos, "label": pads.axis_label(fam, n, pos)} for pos in (False, True)]
            else:             # a trigger: pulled is the only direction
                axes.append({"n": n, "positive": True, "label": pads.axis_label(fam, n, True)})
        out[fam] = {"title": pads.TITLES[fam], "axes": axes,
                    "buttons": [pads.button_label(fam, b, switch_positional) for b in range(L.BUTTONS)]}
    return out


def guess_pad(pokemmo):
    """A pad family PokeMMO has logged on this computer (the last name in its logs), else Xbox.
    Only the starting pick: the player can change it on the page."""
    try:
        names = apply_native.logged_names(Path(pokemmo)) if pokemmo else []
    except OSError:
        names = []
    for name in reversed(names):
        low = name.lower()
        if apply_native.is_nintendo(name):
            return "switch"
        if name in apply_native.PLAYSTATION or "dualsense" in low or "dualshock" in low:
            return "playstation"
        if name in apply_native.XBOX or "xbox" in low or "x-box" in low:
            return "xbox"
    return "xbox"


class App:
    def __init__(self, pokemmo=None, steam=None, no_wheel=False, env=None):
        self.token = secrets.token_urlsafe(24)
        self.pokemmo, self.steam, self.no_wheel = pokemmo, steam, no_wheel
        self.env = env
        self.lock = threading.Lock()
        self.stop = threading.Event()

    # ------------------------------------------------------------ data for the page
    def state(self):
        found, problem = None, None
        try:
            found = str(P.find_pokemmo(self.pokemmo))
        except SystemExit as e:
            problem = str(e).splitlines()[0]
        lay, custom = saved_layout(found) if found else (L.default_layout(), False)
        positional = bool(_record(found).get("switch_positional")) if found else False
        names = pad_names(positional)
        pad = guess_pad(found)
        return {
            "version": VERSION, "layout": lay, "custom": custom, "default": L.default_layout(),
            "pokemmo": found, "problem": problem,
            "actions": [{"id": k, "label": v} for k, v in L.ACTIONS.items()],
            "wheel_actions": [{"id": k, "label": v[1], "key": v[0]} for k, v in L.WHEEL_ACTIONS.items()],
            "pads": names, "pad": pad, "switch_positional": positional,
            "buttons": names[pad]["buttons"], "axes": names[pad]["axes"],
        }

    def check(self, lay):
        L.validate(lay)
        return {"ok": True}

    def diagram(self, lay, pad):
        """The button map (pads.py's picture) of this layout on this pad, as SVG text."""
        if pad not in pads.FAMILIES:
            raise L.LayoutError(f"Unknown controller {pad!r}: pick Xbox, PlayStation or Switch Pro.")
        found = None
        try:
            found = P.find_pokemmo(self.pokemmo)
        except SystemExit:
            pass
        positional = bool(_record(found).get("switch_positional")) if found else False
        return {"ok": True, "svg": pads.render_svg(lay, pad, positional)}

    def apply(self, lay, reset=False):
        """Run setup.py with the layout: one writer for everything."""
        if not reset:
            L.validate(lay)
        cmd = [sys.executable, str(HERE / "setup.py")]
        if self.pokemmo:
            cmd += ["--pokemmo", str(self.pokemmo)]
        if self.steam:
            cmd += ["--steam", str(self.steam)]
        if self.no_wheel:
            cmd.append("--no-wheel")
        tmp = None
        try:
            if reset:
                cmd.append("--reset-layout")
            else:
                fd, tmp = tempfile.mkstemp(prefix="layout-", suffix=".json")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(L.dumps(lay))
                cmd += ["--layout", tmp]
            with self.lock:  # one change at a time
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", env=self.env, stdin=subprocess.DEVNULL, timeout=300)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        out = (r.stdout + r.stderr).strip()
        return {"ok": r.returncode == 0, "output": out}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "pokemmo-controller-ui"
    app = None

    def log_message(self, *a):  # quiet
        pass

    # security: only this computer, only the page we opened
    def _host_ok(self):
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        return host in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; "
                         "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _authorized(self):
        return secrets.compare_digest(self.headers.get("X-Key", ""), self.app.token)

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "wrong host"})
        path, _, query = self.path.partition("?")
        if path == "/":
            if not secrets.compare_digest(query.removeprefix("k=") if query.startswith("k=") else "", self.app.token):
                return self._send(403, "Open the address printed in the terminal, it holds a one-time key.",
                                  "text/plain; charset=utf-8")
            html = PAGE.read_text(encoding="utf-8").replace("__KEY__", self.app.token)
            return self._send(200, html, "text/html; charset=utf-8")
        if path == "/api/state":
            if not self._authorized():
                return self._json(403, {"error": "missing key"})
            return self._json(200, self.app.state())
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "wrong host"})
        if not self._authorized():
            return self._json(403, {"error": "missing key"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._json(415, {"error": "send JSON"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = -1
        if not 0 <= n <= MAX_BODY:
            return self._json(413, {"error": "too big"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self._json(400, {"error": "not JSON"})
        try:
            if self.path == "/api/check":
                return self._json(200, self.app.check(body.get("layout")))
            if self.path == "/api/import":  # a layout file's text
                text = body.get("text")
                if not isinstance(text, str):
                    raise L.LayoutError("No file text was sent.")
                return self._json(200, {"ok": True, "layout": L.loads(text)})
            if self.path == "/api/diagram":
                return self._json(200, self.app.diagram(body.get("layout"), body.get("pad")))
            if self.path == "/api/apply":
                return self._json(200, self.app.apply(body.get("layout")))
            if self.path == "/api/reset":
                return self._json(200, self.app.apply(None, reset=True))
            if self.path == "/api/quit":
                self._json(200, {"ok": True})
                self.app.stop.set()
                return
        except L.LayoutError as e:
            return self._json(200, {"ok": False, "error": str(e)})
        self._json(404, {"error": "not found"})


def make_server(app):
    Handler.app = app
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    return srv


def serve(pokemmo=None, steam=None, no_wheel=False, open_browser=True, env=None):
    app = App(pokemmo, steam, no_wheel, env)
    srv = make_server(app)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?k={app.token}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("Remap screen is running on this computer only.")
    print(f"If your browser did not open, open this address:\n  {url}")
    print("Close this window, or press Quit on the page, to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        while not app.stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    srv.shutdown()
    srv.server_close()
    print("Stopped.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pokemmo")
    ap.add_argument("--steam")
    ap.add_argument("--no-wheel", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    serve(a.pokemmo, a.steam, a.no_wheel, not a.no_browser)
