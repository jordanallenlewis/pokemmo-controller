"""--install-ui keeps a copy of the remap screen on disk with a launcher, and uninstall
removes it again. Without the flag nothing about the install changes."""
import os, subprocess, sys, unittest
from pathlib import Path

import helpers
from test_setup import Base, diff

APP = "pokemmo-controller"


class InstallUi(Base):
    def app_dir(self, sb):
        return sb.pokemmo / APP

    def test_default_install_has_no_app(self):
        sb = self.make()
        sb.setup()
        self.assertFalse(self.app_dir(sb).exists())

    def test_install_rerun_uninstall_restores_every_byte(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--install-ui")
        self.assertIn("Installed", r.stdout)
        app = self.app_dir(sb)
        for rel in ("tools/setup.py", "tools/ui.py", "tools/ui_page.html", "tools/layout.py", "remap.sh", "remap.cmd"):
            self.assertTrue((app / rel).is_file(), rel)
        self.assertIn("remap", r.stdout)
        installed = sb.snapshot()
        # run again with no flag: the app is remembered, nothing changes
        r = sb.setup()
        self.assertIn("Already up to date", r.stdout)
        self.assertSame(installed, sb.snapshot())
        r = sb.setup("--uninstall")
        self.assertIn("Removed", r.stdout)
        self.assertSame(before, sb.snapshot())

    def test_update_refreshes_the_app(self):
        sb = self.make()
        sb.setup("--install-ui")
        app = self.app_dir(sb)
        (app / "tools" / "ui.py").write_text("# an older copy\n")
        sb.setup("--install-ui")
        self.assertEqual((app / "tools" / "ui.py").read_bytes(), (helpers.TOOLS / "ui.py").read_bytes())

    def test_the_installed_copy_runs(self):
        sb = self.make()
        sb.setup("--install-ui")
        r = subprocess.run([sys.executable, str(self.app_dir(sb) / "tools" / "setup.py"), "--version"],
                           capture_output=True, text=True, env=sb.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pokemmo-controller", r.stdout)

    @unittest.skipIf(os.name == "nt", "remap.sh is for macOS and Linux")
    def test_the_shell_launcher_finds_python_and_passes_options(self):
        sb = self.make()
        sb.setup("--install-ui")
        r = subprocess.run(["sh", str(self.app_dir(sb) / "remap.sh"), "--version"],
                           capture_output=True, text=True, env=sb.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pokemmo-controller", r.stdout)

    @unittest.skipIf(os.name == "nt", "remap.sh is for macOS and Linux")
    def test_the_shell_launcher_without_python_says_what_to_do(self):
        sb = self.make()
        sb.setup("--install-ui")
        env = sb.env(PATH=str(sb.root / "empty"))
        (sb.root / "empty").mkdir()
        r = subprocess.run(["/bin/sh", str(self.app_dir(sb) / "remap.sh")], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--ui", r.stderr)

    @unittest.skipUnless(os.name == "nt", "remap.cmd is for Windows")
    def test_the_windows_launcher_finds_python_and_passes_options(self):
        sb = self.make()
        sb.setup("--install-ui")
        r = subprocess.run(["cmd", "/c", str(self.app_dir(sb) / "remap.cmd"), "--version"],
                           capture_output=True, text=True, env=sb.env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pokemmo-controller", r.stdout)

    def test_a_file_the_player_added_to_the_folder_survives_uninstall(self):
        sb = self.make()
        sb.setup("--install-ui")
        keep = self.app_dir(sb) / "my notes.txt"
        keep.write_text("mine")
        sb.setup("--uninstall")
        self.assertEqual(keep.read_text(), "mine")
        self.assertFalse((self.app_dir(sb) / "remap.sh").exists())

    def test_the_app_copy_is_standard_library_only(self):
        import ast
        std = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else None
        local = {p.stem for p in helpers.TOOLS.glob("*.py")}
        for f in helpers.TOOLS.glob("*.py"):
            for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                    [n.module] if isinstance(n, ast.ImportFrom) and n.module else []
                for m in mods:
                    top = m.split(".")[0]
                    if std is not None:
                        self.assertTrue(top in std or top in local, f"{f.name} imports {top}")


if __name__ == "__main__":
    unittest.main()
