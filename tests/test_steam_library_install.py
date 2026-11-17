"""PokeMMO installed through Steam (in any Steam library folder) is found without a flag."""
import subprocess, sys, unittest
from pathlib import Path

from helpers import Sandbox, TOOLS


class SteamLibraryPokeMMO(unittest.TestCase):
    def test_found_in_second_steam_library(self):
        sb = Sandbox()
        lib = sb.home / "Lib2"
        game = lib / "steamapps" / "common" / "PokeMMO"
        (game / "config").mkdir(parents=True)
        (game / "config" / "main.properties").write_text("client.ui.theme=dark\n")
        # the sandbox's own PokeMMO folder is not on the normal search list, so only the vdf leads here
        (sb.steam / "steamapps").mkdir(parents=True, exist_ok=True)
        (sb.steam / "steamapps" / "libraryfolders.vdf").write_text(
            '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % str(lib).replace("\\", "\\\\"))
        code = ("import sys; sys.path.insert(0, r'%s'); import platforms as P; print(P.find_pokemmo())" % TOOLS)
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                           env=sb.env(POKEMMO_CONTROLLER_STEAM_DIR=str(sb.steam)))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(r.stdout.strip()).resolve(), game.resolve())

    def test_not_found_message_lists_steam_libraries(self):
        sb = Sandbox()
        (sb.pokemmo / "config" / "main.properties").unlink(missing_ok=True)
        code = ("import sys; sys.path.insert(0, r'%s'); import platforms as P; P.find_pokemmo()" % TOOLS)
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                           env=sb.env(POKEMMO_CONTROLLER_STEAM_DIR=str(sb.steam)))
        self.assertNotEqual(r.returncode, 0)


class OtherDrives(unittest.TestCase):
    def test_other_drive_search_never_raises_and_is_silent_in_tests(self):
        code = ("import sys; sys.path.insert(0, r'%s'); import platforms as P; "
                "print(len(P._other_drive_folders()))" % TOOLS)
        sb = Sandbox()
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=sb.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "0")  # sandbox runs never look at the real machine's drives


if __name__ == "__main__":
    unittest.main()
