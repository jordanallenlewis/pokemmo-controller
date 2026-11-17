"""Tests that start a process or build a sandbox clean up after themselves.

An output pipe left open, or a temp folder left for the garbage collector, shows up as a
ResourceWarning. On Windows an open handle can also keep a folder from being deleted and make a
later test fail for no reason of its own. This runs the tests that start processes or build
sandboxes by hand, with those warnings shown, and fails if any appear.
"""
import os, subprocess, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Tests that start a long-running process or build a Sandbox outside a make()/addCleanup helper.
WATCHED = [
    "test_steam_library_install",
    "test_ui.Launch",
    "test_live_resolution.Following",
    "test_login_helper.OneCopyAtATime",
]


class NoLeaks(unittest.TestCase):
    def test_no_open_pipe_or_temp_folder_is_left_behind(self):
        env = dict(os.environ)
        env.pop("PYTHONWARNINGS", None)
        r = subprocess.run([sys.executable, "-W", "always::ResourceWarning", "-m", "unittest", *WATCHED],
                           cwd=str(HERE), env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300, stdin=subprocess.DEVNULL)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-3000:])
        leaks = [line for line in out.splitlines() if "ResourceWarning" in line]
        self.assertEqual(leaks, [], out[-3000:])


if __name__ == "__main__":
    unittest.main()
