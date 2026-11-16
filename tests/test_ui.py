"""The remap screen's server: who may talk to it, what it refuses, and that Apply goes
through the same installer (setup.py) as everything else. No browser needed."""
import http.client, json, threading, unittest

import helpers  # noqa: F401  (tools/ on the path, test mode on)
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

    def test_state(self):
        self.start(self.make())
        code, st = self.call("GET", "/api/state")
        self.assertEqual(code, 200)
        self.assertEqual(st["layout"], L.default_layout())
        self.assertFalse(st["custom"])
        self.assertEqual(len(st["buttons"]), L.BUTTONS)
        self.assertEqual(len(st["wheel_actions"]), L.WHEEL_SIZE)

    def test_macros_refused_by_check_and_import_and_apply(self):
        sb = self.make()
        self.start(sb)
        before = sb.snapshot()
        bad = L.default_layout()
        bad["binds"]["KEY_A"] = {"button": 0, "turbo": True}
        dup = L.default_layout()
        dup["binds"]["KEY_SCREENSHOT"] = {"button": 0}
        for lay in (bad, dup):
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
        self.assertEqual(self.call("POST", "/api/check", raw="x" * (ui.MAX_BODY + 10))[0], 413)
        self.assertEqual(self.call("POST", "/api/nothing", {})[0], 404)
        self.assertEqual(self.call("GET", "/api/nothing")[0], 404)

    def test_apply_then_reset_then_uninstall(self):
        sb = self.make()
        self.start(sb)
        before = sb.snapshot()
        lay = L.default_layout()
        lay["binds"]["KEY_INVENTORY"], lay["binds"]["KEY_HOTBAR_5"] = ({"button": 9}, {"button": 10})
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
