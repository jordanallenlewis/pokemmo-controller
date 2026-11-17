"""The remap screen's server: who may talk to it, what it refuses, and that Apply goes
through the same installer (setup.py) as everything else. No browser needed."""
import http.client, http.server, json, threading, unittest

import helpers  # noqa: F401  (tools/ on the path, test mode on)
import common
import layout as L
import ui
from test_setup import Base, diff


class UI(Base):
    def start(self, sb):
        app = ui.App(pokemmo=str(sb.pokemmo), steam=str(sb.steam), env=sb.env())
        srv = ui.make_server(app)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        self.app, self.port = app, srv.server_address[1]
        return app

    def call(self, method, path, body=None, key=True, host=None, ctype="application/json", raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        if key:
            h["X-Key"] = self.app.token
        data = raw if raw is not None else (json.dumps(body) if body is not None else None)
        if data is not None:
            h["Content-Type"] = ctype
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        text = r.read().decode("utf-8")
        c.close()
        try:
            return r.status, json.loads(text)
        except ValueError:
            return r.status, text

    def test_page_needs_the_one_time_key(self):
        self.start(self.make())
        self.assertEqual(self.call("GET", "/", key=False)[0], 403)
        self.assertEqual(self.call("GET", "/?k=wrong", key=False)[0], 403)
        code, html = self.call("GET", f"/?k={self.app.token}", key=False)
        self.assertEqual(code, 200)
        self.assertIn(self.app.token, html)
        self.assertNotIn("__KEY__", html)

    def test_other_hosts_are_refused(self):
        self.start(self.make())
        for host in ("evil.example", f"evil.example:{self.port}", "127.0.0.1", f"192.168.1.5:{self.port}"):
            self.assertEqual(self.call("GET", "/api/state", host=host)[0], 403, host)
            self.assertEqual(self.call("POST", "/api/check", {"layout": L.default_layout()}, host=host)[0], 403)

    def test_api_needs_the_key(self):
        self.start(self.make())
        self.assertEqual(self.call("GET", "/api/state", key=False)[0], 403)
        self.assertEqual(self.call("POST", "/api/apply", {"layout": L.default_layout()}, key=False)[0], 403)

    def test_page_sends_no_third_party_requests(self):
        self.start(self.make())
        html = self.call("GET", f"/?k={self.app.token}", key=False)[1]
        self.assertNotIn("http://", html.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("https://", html)

    def test_status_reports_what_the_install_record_says(self):
        self.start(self.make())
        self.assertEqual(self.call("GET", "/api/status", key=False)[0], 403)
        code, st = self.call("GET", "/api/status")
        self.assertEqual(code, 200)
        self.assertTrue(st["pokemmo"])
        self.assertFalse(st["installed"] or st["binds"] or st["steam"], "nothing installed yet in this sandbox")
        self.assertEqual(self.call("GET", "/api/state")[1]["status"], st)
        phys = self.call("GET", "/api/state")[1]["phys"]
        self.assertEqual(sorted(phys["xbox"]), list(range(L.BUTTONS)))
        self.assertEqual(sorted(phys["switch"]), list(range(L.BUTTONS)), "every button sits on exactly one spot")

    def test_status_tells_whether_what_is_installed_is_still_right(self):
        sb = self.make()
        sb.setup()
        self.start(sb)
        st = self.call("GET", "/api/status")[1]
        self.assertTrue(st["installed"] and st["binds_current"] and st["steam_current"], st)
        self.assertFalse(st["pokemmo_open"])
        # the game rewrote its settings without our binds: the record says installed, the truth is not
        props = sb.pokemmo / "config" / "main.properties"
        text = props.read_text(encoding="utf-8")
        props.write_text("\n".join(l for l in text.splitlines() if not l.startswith(common.MAP_KEY)) + "\n",
                         encoding="utf-8")
        st = self.call("GET", "/api/status")[1]
        self.assertTrue(st["installed"])
        self.assertFalse(st["binds_current"], "binds gone: must not tick")
        self.assertTrue(st["steam_current"])
        # and the one-click fix puts them back
        self.assertTrue(self.call("POST", "/api/apply", {"layout": L.default_layout()})[1]["ok"])
        self.assertTrue(self.call("GET", "/api/status")[1]["binds_current"])

    def test_status_notices_a_missing_steam_layout(self):
        sb = self.make()
        sb.setup()
        self.start(sb)
        for f in sb.layout_dir.glob("*") if hasattr(sb, "layout_dir") else []:
            f.unlink()
        cfg = sb.steam / "steamapps" / "common" / "Steam Controller Configs"
        files = [f for f in cfg.rglob("*") if f.is_file()]
        self.assertTrue(files, "the wheel layouts exist after install")
        for f in files:
            f.unlink()
        st = self.call("GET", "/api/status")[1]
        self.assertFalse(st["steam_current"])
        self.assertTrue(st["binds_current"])

    def test_status_is_unknown_not_green_when_nothing_is_installed(self):
        self.start(self.make())
        st = self.call("GET", "/api/status")[1]
        self.assertFalse(st["binds_current"])
        self.assertFalse(st["steam_current"])

    def test_state(self):
        self.start(self.make())
        code, st = self.call("GET", "/api/state")
        self.assertEqual(code, 200)
        self.assertEqual(st["layout"], L.default_layout())
        self.assertFalse(st["custom"])
        self.assertEqual(len(st["buttons"]), L.BUTTONS)
        self.assertEqual(len(st["wheel_actions"]), L.WHEEL_SIZE)

    def test_state_names_every_pad_by_its_own_buttons(self):
        self.start(self.make())
        st = self.call("GET", "/api/state")[1]
        self.assertEqual(set(st["pads"]), {"xbox", "playstation", "switch"})
        for fam, p in st["pads"].items():
            self.assertEqual(len(p["buttons"]), L.BUTTONS, fam)
            self.assertTrue(p["title"])
            self.assertEqual({a["n"] for a in p["axes"]}, {0, 1, 4, 5}, fam)   # never the wheel's stick
        self.assertEqual(st["pads"]["xbox"]["buttons"][0], "A")
        self.assertEqual(st["pads"]["playstation"]["buttons"][0], "Cross")
        # default Switch setting: the printed A confirms, so the confirm spot is called A
        self.assertEqual(st["pads"]["switch"]["buttons"][:4], ["A", "B", "X", "Y"])
        self.assertFalse(st["switch_positional"])
        self.assertEqual(st["pad"], "xbox")   # an 8BitDo pad is logged in the sandbox: no guess, Xbox names

    def test_switch_names_follow_the_installed_setting(self):
        sb = self.make()
        sb.setup("--switch-positional")
        self.start(sb)
        st = self.call("GET", "/api/state")[1]
        self.assertTrue(st["switch_positional"])
        self.assertEqual(st["pads"]["switch"]["buttons"][:4], ["B", "A", "Y", "X"])

    def test_pad_guess_from_the_pads_pokemmo_logged(self):
        for line, fam in (("DualSense Wireless Controller", "playstation"),
                          ("Nintendo Switch Pro Controller", "switch"),
                          ("Xbox Series X Controller", "xbox")):
            sb = self.make()
            (sb.pokemmo / "log" / "client.log").write_text(
                f"[INFO] Controller {line} ( ax 6 btn 15) id 0 attached\n", encoding="utf-8")
            self.start(sb)
            self.assertEqual(self.call("GET", "/api/state")[1]["pad"], fam, line)

    def test_diagram_draws_the_layout_on_the_chosen_pad(self):
        import xml.etree.ElementTree as ET
        self.start(self.make())
        lay = L.default_layout()
        lay["binds"]["KEY_INVENTORY"], lay["binds"]["KEY_RING_FOCUS"] = ({"button": 9}, {"button": 10})
        del lay["binds"]["KEY_TEAM"]
        for fam, word in (("xbox", "LB"), ("playstation", "Cross"), ("switch", "ZR")):
            code, r = self.call("POST", "/api/diagram", {"layout": lay, "pad": fam})
            self.assertEqual(code, 200)
            self.assertTrue(r["ok"], r)
            text = " ".join(ET.fromstring(r["svg"]).itertext())
            self.assertIn(word, text)
            self.assertIn("Not bound", text)
            self.assertNotIn("<script", r["svg"])
        bad = L.default_layout()
        bad["binds"]["KEY_A"] = {"button": 0, "turbo": True}
        self.assertFalse(self.call("POST", "/api/diagram", {"layout": bad, "pad": "xbox"})[1]["ok"])
        self.assertFalse(self.call("POST", "/api/diagram", {"layout": lay, "pad": "gamecube"})[1]["ok"])
        self.assertEqual(self.call("POST", "/api/diagram", {"layout": lay, "pad": "xbox"}, key=False)[0], 403)

    def test_macros_refused_by_check_and_import_and_apply(self):
        sb = self.make()
        self.start(sb)
        before = sb.snapshot()
        bad = L.default_layout()
        bad["binds"]["KEY_A"] = {"button": 0, "turbo": True}
        dup = L.default_layout()
        dup["binds"]["KEY_SCREENSHOT"] = {"button": 0}
        pushed = L.default_layout()   # a trigger never reports the "pushed away" direction
        pushed["binds"]["KEY_SCREENSHOT"] = {"axis": 4, "positive": False}
        for lay in (bad, dup, pushed):
            r = self.call("POST", "/api/check", {"layout": lay})[1]
            self.assertFalse(r["ok"])
            r = self.call("POST", "/api/import", {"text": json.dumps(lay)})[1]
            self.assertFalse(r["ok"])
            r = self.call("POST", "/api/apply", {"layout": lay})[1]
            self.assertFalse(r["ok"])
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_bad_requests(self):
        self.start(self.make())
        self.assertEqual(self.call("POST", "/api/check", raw="{", )[0], 400)
        self.assertEqual(self.call("POST", "/api/check", raw="[]")[0], 400)
        self.assertEqual(self.call("POST", "/api/check", {"layout": 1}, ctype="text/plain")[0], 415)
        # The server refuses a too-big body without reading it. Depending on timing the client
        # sees the 413 or (macOS) the connection reset while it is still sending: both are a refusal.
        try:
            self.assertEqual(self.call("POST", "/api/check", raw="x" * (ui.MAX_BODY + 10))[0], 413)
        except (ConnectionError, OSError):
            pass
        self.assertEqual(self.call("POST", "/api/nothing", {})[0], 404)
        self.assertEqual(self.call("GET", "/api/nothing")[0], 404)

    def test_refusals_read_the_body_first(self):
        # A server that closes a connection with request bytes still unread makes Windows send a
        # reset, and the browser (or a test) can lose the answer that was already sent: Apply from
        # a page left open with an old key showed a network error, not "missing key". So every
        # refusal reads the body it was sent (up to MAX_BODY) before answering. Checked on the
        # server side, the same on every OS: what is left unread when the answer is done.
        app = ui.App(pokemmo=str(self.make().pokemmo), steam=None)
        ui.make_server(app).server_close()  # sets Handler.app
        left = []

        class Probe(ui.Handler):
            def finish(self):
                old = self.connection.gettimeout()
                self.connection.settimeout(0)
                n = 0
                try:
                    while True:
                        chunk = self.rfile.read1(65536)
                        if not chunk:
                            break
                        n += len(chunk)
                except OSError:
                    pass
                self.connection.settimeout(old)
                left.append(n)
                super().finish()

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Probe)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        self.app, self.port = app, srv.server_address[1]
        ok = f"127.0.0.1:{self.port}"
        big = {"layout": L.default_layout(), "pad": "x" * 30000}  # larger than the read buffer
        cases = [  # (host, key, content type, expected answer)
            ("evil.example", app.token, "application/json", 403),
            (ok, None, "application/json", 403),
            (ok, "stale-key-from-an-old-page", "application/json", 403),
            (ok, app.token, "text/plain", 415),
        ]
        for body in ({"layout": 1}, big):
            for host, key, ctype, want in cases:
                del left[:]
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
                h = {"Host": host, "Content-Type": ctype}
                if key:
                    h["X-Key"] = key
                c.request("POST", "/api/apply", body=json.dumps(body), headers=h)
                r = c.getresponse()
                self.assertEqual(r.status, want, (host, key, ctype))
                self.assertIn("error", json.loads(r.read().decode("utf-8")))
                c.close()
                for _ in range(100):  # finish() runs just after the answer is sent
                    if left:
                        break
                    threading.Event().wait(0.05)
                self.assertEqual(left, [0], (host, key, ctype, len(json.dumps(body))))

    def test_apply_then_reset_then_uninstall(self):
        sb = self.make()
        self.start(sb)
        before = sb.snapshot()
        lay = L.default_layout()
        lay["binds"]["KEY_INVENTORY"], lay["binds"]["KEY_RING_FOCUS"] = ({"button": 9}, {"button": 10})
        r = self.call("POST", "/api/apply", {"layout": lay})[1]
        self.assertTrue(r["ok"], r)
        self.assertIn("KEY_INVENTORY,BUTTON,9", sb.props.read_text(encoding="utf-8"))
        st = self.call("GET", "/api/state")[1]
        self.assertTrue(st["custom"])
        self.assertEqual(st["layout"], lay)
        r = self.call("POST", "/api/reset", {})[1]
        self.assertTrue(r["ok"], r)
        self.assertIn("KEY_INVENTORY,BUTTON,10", sb.props.read_text(encoding="utf-8"))
        self.assertFalse(self.call("GET", "/api/state")[1]["custom"])
        sb.setup("--uninstall")
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_quit(self):
        app = self.start(self.make())
        self.assertFalse(app.stop.is_set())
        self.call("POST", "/api/quit", {})
        self.assertTrue(app.stop.wait(5))


if __name__ == "__main__":
    unittest.main()


class Launch(Base):
    """`setup.py --ui` as a player runs it: starts, serves the page, stops on Quit."""

    def test_setup_ui_starts_serves_and_quits(self):
        import re, subprocess, sys, urllib.request
        from helpers import TOOLS
        sb = self.make()
        p = subprocess.Popen([sys.executable, "-u", str(TOOLS / "setup.py"), "--ui", "--no-browser",
                              "--pokemmo", str(sb.pokemmo), "--no-wheel"], env=sb.env(),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        self.addCleanup(lambda: p.poll() is None and p.kill())
        url = None
        for line in p.stdout:
            m = re.search(r"http://127\.0\.0\.1:(\d+)/\?k=(\S+)", line)
            if m:
                url = m
                break
        self.assertIsNotNone(url, "no address printed")
        html = urllib.request.urlopen(url.group(0), timeout=30).read().decode("utf-8")
        self.assertIn("PokeMMO controller layout", html)
        req = urllib.request.Request(f"http://127.0.0.1:{url.group(1)}/api/quit", data=b"{}", method="POST",
                                     headers={"X-Key": url.group(2), "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30).read()
        self.assertEqual(p.wait(timeout=30), 0)
