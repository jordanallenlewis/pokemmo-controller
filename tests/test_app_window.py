"""The remap screen gets its own window (a browser in app mode), with nothing to install.

No test here opens a real window: the launcher is pure (candidates and command lines) and the
actual start is injected."""
import os, tempfile, unittest
from pathlib import Path

import helpers  # noqa: F401
import platforms as P


def fake_exe(d, name):
    p = Path(d, name)
    p.write_text("x")
    p.chmod(0o755)
    return str(p)


class Command(unittest.TestCase):
    def test_app_mode_flags_and_the_address(self):
        cmd = P.app_window_command("/b/chrome", "http://127.0.0.1:5/?k=a", "/p")
        self.assertEqual(cmd[0], "/b/chrome")
        self.assertIn("--app=http://127.0.0.1:5/?k=a", cmd)
        self.assertIn("--user-data-dir=/p", cmd)         # its own process: closing the window ends it
        self.assertTrue(any(a.startswith("--window-size=") for a in cmd))
        self.assertIn("--no-first-run", cmd)

    def test_only_the_local_address_is_ever_opened(self):
        for bad in ("https://example.com/", "file:///etc/passwd", "http://127.0.0.1.evil.com/"):
            with self.assertRaises(ValueError):
                P.app_window_command("/b/chrome", bad, "/p")


class Find(unittest.TestCase):
    def test_sandbox_mode_never_finds_the_real_machines_browsers(self):
        self.assertTrue(P.TEST)
        self.assertEqual(P.app_browser_candidates(), [])
        self.assertIsNone(P.find_app_browser())

    def test_override_wins_and_must_exist(self):
        with tempfile.TemporaryDirectory() as d:
            exe = fake_exe(d, "mybrowser")
            self.assertEqual(P.find_app_browser(override=exe), exe)
            self.assertIsNone(P.find_app_browser(override=str(Path(d, "nope"))))

    def test_override_by_environment(self):
        with tempfile.TemporaryDirectory() as d:
            exe = fake_exe(d, "mybrowser")
            old = os.environ.get("POKEMMO_CONTROLLER_BROWSER")
            os.environ["POKEMMO_CONTROLLER_BROWSER"] = exe
            try:
                self.assertEqual(P.find_app_browser(), exe)
            finally:
                os.environ.pop("POKEMMO_CONTROLLER_BROWSER") if old is None else os.environ.update(POKEMMO_CONTROLLER_BROWSER=old)

    def test_the_real_machine_query_cannot_raise(self):
        was, P.TEST = P.TEST, False
        try:
            P.app_browser_candidates()
            P.find_app_browser()
        finally:
            P.TEST = was

    def test_every_system_names_a_browser_that_is_always_there_first(self):
        for win, mac in ((True, False), (False, True), (False, False)):
            names = P._app_browser_names(win, mac)
            self.assertTrue(names)
        self.assertIn("msedge.exe", [n.replace("\\", "/").rsplit("/", 1)[-1] for n in P._app_browser_names(True, False)])


class Open(unittest.TestCase):
    def test_opens_app_window_and_reports_it(self):
        started = []
        with tempfile.TemporaryDirectory() as d:
            exe = fake_exe(d, "b")
            proc = P.open_app_window("http://127.0.0.1:9/?k=z", override=exe, profile=d,
                                     start=lambda cmd: started.append(cmd) or "PROC")
        self.assertEqual(proc, "PROC")
        self.assertEqual(started[0][0], exe)

    def test_none_when_no_browser_so_the_caller_falls_back_to_a_tab(self):
        self.assertIsNone(P.open_app_window("http://127.0.0.1:9/?k=z", start=lambda c: self.fail("started")))

    def test_a_browser_that_will_not_start_is_not_an_error(self):
        def boom(cmd):
            raise OSError("no")
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(P.open_app_window("http://127.0.0.1:9/?k=z", override=fake_exe(d, "b"),
                                                profile=d, start=boom))


if __name__ == "__main__":
    unittest.main()


class Serve(unittest.TestCase):
    class Proc:
        def __init__(self, lifetime, clock):
            self.lifetime, self.clock = lifetime, clock

        def wait(self):
            self.clock.t += self.lifetime

    class Clock:
        t = 0.0

        def __call__(self):
            return self.t

    def watch(self, lifetime):
        import ui
        clock = self.Clock()
        app = type("A", (), {"stop": __import__("threading").Event()})()
        return ui.watch_window(self.Proc(lifetime, clock), app, clock=clock), app.stop.is_set()

    def test_closing_the_window_quits_the_app(self):
        self.assertEqual(self.watch(60), (True, True))

    def test_a_window_that_vanishes_at_once_falls_back_to_a_tab_and_keeps_running(self):
        self.assertEqual(self.watch(0.5), (False, False))

    def test_serve_opens_the_window_not_a_tab_and_a_tab_when_asked(self):
        import threading, ui
        for tab, expect in ((False, ["window"]), (True, ["tab"])):
            seen = []
            real = ui.webbrowser.open
            ui.webbrowser.open = lambda u, seen=seen: seen.append("tab")
            holder = {}
            orig = ui.App

            class A(orig):
                def __init__(s, *a, **k):
                    super().__init__(*a, **k)
                    holder["app"] = s
                    threading.Timer(0.3, s.stop.set).start()
            ui.App = A
            try:
                class P:
                    def wait(self):
                        threading.Event().wait(5)
                ui.serve(None, None, True, True, tab=tab,
                         open_window=lambda u: seen.append("window") or P())
            finally:
                ui.App, ui.webbrowser.open = orig, real
            self.assertEqual(seen, expect)
