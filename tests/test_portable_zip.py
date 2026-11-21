"""PokeMMO unzipped from its portable ZIP (Downloads/PokeMMO-Client and friends) is found without a flag.

PokeMMO-Client.zip has no top folder, so Windows "Extract All" and Linux file managers unzip it
into a new PokeMMO-Client folder next to the zip, usually in Downloads.
"""
import json, subprocess, sys, unittest
from pathlib import Path

from helpers import Sandbox, TOOLS


def portable_copy(folder):
    """Lay out the parts of the portable ZIP the installer looks at."""
    (folder / "config").mkdir(parents=True)
    (folder / "config" / "main.properties").write_text("client.ui.theme=dark\n")
    (folder / "PokeMMO.exe").write_bytes(b"")
    (folder / "PokeMMO.sh").write_text("#!/bin/sh\n")
    return folder


class PortableZip(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.addCleanup(self.sb.cleanup)
        # the sandbox's own PokeMMO folder is not on the search list, so only the new places lead here

    def run_py(self, code, **env):
        prog = "import sys, json; sys.path.insert(0, r'%s'); import platforms as P; %s" % (TOOLS, code)
        return subprocess.run([sys.executable, "-X", "utf8", "-I", "-c", prog], capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              env=self.sb.env(POKEMMO_CONTROLLER_STEAM_DIR=str(self.sb.steam),
                                              PYTHONIOENCODING="utf-8", **env))

    def find(self, **env):
        r = self.run_py("print(P.find_pokemmo())", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return Path(r.stdout.strip()).resolve()

    def test_found_in_downloads_desktop_and_documents(self):
        for where in ("Downloads", "Desktop", "Documents"):
            with self.subTest(where=where):
                game = portable_copy(self.sb.home / where / "PokeMMO-Client")
                self.assertEqual(self.find(), game.resolve())
                (game / "config" / "main.properties").unlink()

    def test_found_as_plain_pokemmo_folder_in_downloads(self):
        game = portable_copy(self.sb.home / "Downloads" / "PokeMMO")
        self.assertEqual(self.find(), game.resolve())

    def test_found_in_onedrive_desktop(self):
        game = portable_copy(self.sb.home / "OneDrive" / "Desktop" / "PokeMMO-Client")
        self.assertEqual(self.find(), game.resolve())

    def test_found_in_translated_download_folder(self):
        # Linux desktops name the folder in the user's language and record it in user-dirs.dirs
        cfg = self.sb.home / ".config"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "user-dirs.dirs").write_text(
            '# written by xdg-user-dirs-update\nXDG_DESKTOP_DIR="$HOME/Bureau"\n'
            'XDG_DOWNLOAD_DIR="$HOME/Téléchargements"\n', encoding="utf-8")
        game = portable_copy(self.sb.home / "Téléchargements" / "PokeMMO-Client")
        self.assertEqual(self.find(), game.resolve())

    @unittest.skipUnless(sys.platform.startswith("linux"), "the Debian/Ubuntu pokemmo-installer folder only exists on Linux")
    def test_debian_pokemmo_installer_folder(self):
        # the pokemmo-installer script (Debian/Ubuntu) uses $XDG_DATA_HOME/pokemmo, lower case
        game = portable_copy(self.sb.home / ".local" / "share" / "pokemmo")
        self.assertEqual(self.find(), game.resolve())

    def test_a_real_install_wins_over_an_old_unzipped_copy(self):
        portable_copy(self.sb.home / "Downloads" / "PokeMMO-Client")
        real = portable_copy(self.sb.home / ("Library/Application Support/com.pokeemu.macos/pokemmo-client-live"
                                             if sys.platform == "darwin" else "Games/PokeMMO"))
        self.assertEqual(self.find(), real.resolve())

    def test_a_steam_copy_wins_over_an_old_unzipped_copy(self):
        portable_copy(self.sb.home / "Downloads" / "PokeMMO-Client")
        lib = self.sb.home / "Lib2"
        game = portable_copy(lib / "steamapps" / "common" / "PokeMMO")
        (self.sb.steam / "steamapps").mkdir(parents=True, exist_ok=True)
        (self.sb.steam / "steamapps" / "libraryfolders.vdf").write_text(
            '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % str(lib).replace("\\", "\\\\"))
        self.assertEqual(self.find(), game.resolve())

    def test_not_found_message_names_the_new_places(self):
        r = self.run_py("P.find_pokemmo()")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(str(Path("Downloads") / "PokeMMO-Client"), r.stderr)
        self.assertIn(str(Path("Desktop") / "PokeMMO-Client"), r.stderr)

    def test_a_broken_user_dirs_file_is_ignored(self):
        cfg = self.sb.home / ".config"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "user-dirs.dirs").write_bytes(b'XDG_DOWNLOAD_DIR="\xff\xfe\n\x00garbage\nXDG_DESKTOP_DIR=/abs/out\n')
        game = portable_copy(self.sb.home / "Downloads" / "PokeMMO-Client")
        self.assertEqual(self.find(), game.resolve())

    @unittest.skipIf(sys.platform == "win32" or (hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() == 0),
                     "needs a non-root user on a system with permission bits")
    def test_an_unreadable_downloads_folder_is_skipped(self):
        game = portable_copy(self.sb.home / "Desktop" / "PokeMMO-Client")
        down = self.sb.home / "Downloads"
        down.mkdir()
        down.chmod(0)
        self.addCleanup(down.chmod, 0o755)
        self.assertEqual(self.find(), game.resolve())

    def test_steam_shortcut_starts_the_portable_copy(self):
        game = portable_copy(self.sb.home / "Downloads" / "PokeMMO-Client")
        r = self.run_py("print(json.dumps(P.shortcut_target(P.find_pokemmo())))")
        self.assertEqual(r.returncode, 0, r.stderr)
        exe, start, _ = json.loads(r.stdout)
        if sys.platform == "darwin" and (Path("/Applications/PokeMMO.app").exists()
                                         or (Path.home() / "Applications/PokeMMO.app").exists()):
            self.skipTest("this Mac has the PokeMMO app, which the shortcut starts instead")
        want = "PokeMMO.exe" if sys.platform == "win32" else "PokeMMO.sh"
        self.assertEqual(Path(exe.strip('"')).resolve(), (game / want).resolve())
        self.assertEqual(Path(start.strip('"')).resolve(), game.resolve())


if __name__ == "__main__":
    unittest.main()
