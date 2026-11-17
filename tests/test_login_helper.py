"""The wheel follower starts at login by default: one entry per platform, tracked in the install
record, removed by uninstall, one copy at a time, and it ends by itself when the layout is gone.
It never touches the game and sends no input."""
import json, os, subprocess, sys, time, unittest
from pathlib import Path

from helpers import Sandbox, TOOLS
import platforms as P
from test_setup import Base


def record(sb):
    return json.loads((sb.pokemmo / "config" / "pokemmo-controller.json").read_text(encoding="utf-8"))


class LoginEntry(Base):
    def test_default_install_adds_one_entry_and_uninstall_removes_it_byte_for_byte(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup(login=True)
        self.assertIn("starts when you log in", r.stdout)
        entries = [Path(x) for x in record(sb)["autostart"]]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].is_file())
        self.assertTrue(str(entries[0]).startswith(str(sb.home)))          # the user's own folder, no admin
        app = sb.pokemmo / "pokemmo-controller"
        self.assertTrue((app / "tools" / "setup.py").is_file())
        self.assertTrue((app / ("follow.cmd" if os.name == "nt" else "follow.sh")).is_file())
        self.assertNotIn("remap screen", r.stdout.split("starts when you log in")[1])   # the screen was not asked for
        self.assertIsNone(record(sb).get("app"))
        sb.setup("--uninstall", login=True)
        self.assertSame(before, sb.snapshot())

    def test_entry_names_the_launcher_and_the_follower_runs_in_the_background(self):
        sb = self.make()
        sb.setup(login=True)
        entry = Path(record(sb)["autostart"][0])
        raw = entry.read_bytes()
        text = raw.decode("utf-16") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8")
        self.assertIn("follow." + ("cmd" if os.name == "nt" else "sh"), text)
        launcher = sb.pokemmo / "pokemmo-controller" / ("follow.cmd" if os.name == "nt" else "follow.sh")
        self.assertIn("--follow --background", launcher.read_text())

    def test_no_follow_is_remembered_by_later_runs_and_follow_at_login_turns_it_back_on(self):
        sb = self.make()
        sb.setup("--no-follow", login=True)
        self.assertFalse(record(sb).get("autostart"))
        self.assertIs(record(sb)["follow"], False)
        sb.setup(login=True)                                   # a rerun keeps the choice
        self.assertFalse(record(sb).get("autostart"))
        sb.setup("--follow-at-login", login=True)
        entries = [Path(x) for x in record(sb)["autostart"]]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].is_file())
        sb.setup("--no-follow", login=True)                    # and turning it off removes the entry
        self.assertFalse(entries[0].exists())
        self.assertFalse(record(sb).get("autostart"))

    def test_an_update_from_the_previous_version_gets_the_helper(self):
        sb = self.make()
        sb.setup("--no-follow", login=True)
        st = record(sb)
        st.pop("follow")                                        # what v1.1.0 wrote: no such key
        (sb.pokemmo / "config" / "pokemmo-controller.json").write_text(json.dumps(st), encoding="utf-8")
        sb.setup(login=True)
        self.assertEqual(len(record(sb)["autostart"]), 1)

    def test_without_steam_there_is_no_wheel_to_follow(self):
        sb = self.make(steam=False)
        sb.setup("--no-wheel", steam=False, login=True)
        self.assertFalse(record(sb).get("autostart"))

    def test_dry_run_lists_the_entry_and_writes_nothing(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--dry-run", login=True)
        self.assertIn("would create", r.stdout)
        self.assertSame(before, sb.snapshot())

    def test_a_computer_without_python_says_so_and_adds_no_entry(self):
        sb = self.make()
        r = subprocess.run([sys.executable, "-c", (
            "import sys; sys.path.insert(0, %r); import platforms as P; P.python_for_login = lambda: False; "
            "import setup; sys.argv = ['setup.py', '--pokemmo', %r, '--steam', %r]; setup.main()"
        ) % (str(TOOLS), str(sb.pokemmo), str(sb.steam))], env=sb.env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("install Python 3.9", r.stdout)
        self.assertFalse(record(sb).get("autostart"))
        self.assertTrue(sb.props.exists())                      # the install itself still worked


class Contents(unittest.TestCase):
    def test_every_platform_entry_is_valid_for_a_path_with_spaces_and_odd_characters(self):
        tricky = Path("/Users/Zoë Müller/Poke MMO/pokemmo-controller/follow.sh")
        for name, text in (("windows", None), ("mac", None), ("linux", None)):
            old = (P.WINDOWS, P.MAC)
            P.WINDOWS, P.MAC = name == "windows", name == "mac"
            try:
                (path, data), = P.login_entries(tricky).items()
            finally:
                P.WINDOWS, P.MAC = old
            if name == "windows":
                self.assertTrue(data.startswith(b"\xff\xfe"))
                self.assertIn(str(tricky), data.decode("utf-16"))
                self.assertEqual(path.suffix, ".vbs")
            elif name == "mac":
                import plistlib
                self.assertEqual(plistlib.loads(data)["ProgramArguments"], ["/bin/sh", str(tricky)])
                self.assertTrue(plistlib.loads(data)["RunAtLoad"])
            else:
                self.assertIn(f'Exec=sh "{tricky}"', data.decode("utf-8"))
                self.assertEqual(path.suffix, ".desktop")

    def test_the_login_entry_has_one_job_and_sends_no_input(self):
        src = (TOOLS / "fit.py").read_text() + (TOOLS / "app.py").read_text()
        for word in ("SendInput", "keybd_event", "xdotool", "pyautogui", "CGEvent"):
            self.assertNotIn(word, src)


class OneCopyAtATime(Base):
    def _run(self, sb, *extra, polls=None, interval="0.05"):
        env = sb.env(POKEMMO_CONTROLLER_TEST_POLLS=str(polls)) if polls else sb.env()
        sz = sb.root / "size.txt"
        sz.write_text("1920x1080")
        env["POKEMMO_CONTROLLER_TEST_SIZE_FILE"] = str(sz)
        env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(sb.root)      # the lock lives in the sandbox
        return subprocess.Popen([sys.executable, str(TOOLS / "setup.py"), "--pokemmo", str(sb.pokemmo),
                                 "--steam", str(sb.steam), "--follow", "--background",
                                 "--follow-interval", interval, *extra],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_a_second_follower_for_the_same_folder_ends_at_once(self):
        sb = self.make()
        sb.setup(login=True)
        first = self._run(sb, polls=100000)
        try:
            time.sleep(1.5)
            self.assertIsNone(first.poll(), first.stderr.read() if first.poll() is not None else "")
            second = self._run(sb, polls=100000)
            out, err = second.communicate(timeout=30)
            self.assertEqual(second.returncode, 0, err)
            self.assertIsNone(first.poll())                     # the first one is still the follower
        finally:
            first.kill()
            first.communicate()

    def test_the_follower_ends_when_the_layout_is_uninstalled_and_prints_nothing(self):
        sb = self.make()
        sb.setup(login=True)
        f = self._run(sb, polls=100000)
        try:
            time.sleep(1.5)
            self.assertIsNone(f.poll())
            sb.setup("--uninstall", login=True)
            out, err = f.communicate(timeout=30)
            self.assertEqual(f.returncode, 0, err)
            self.assertEqual(out.strip(), "")
        finally:
            if f.poll() is None:
                f.kill()
                f.communicate()

    def test_a_follower_started_before_the_layout_exists_just_ends(self):
        sb = self.make()
        f = self._run(sb, polls=5)
        out, err = f.communicate(timeout=30)
        self.assertEqual(f.returncode, 0, err)
        self.assertEqual(out.strip(), "")

    def test_background_needs_follow(self):
        sb = self.make()
        r = sb.setup("--background", check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
