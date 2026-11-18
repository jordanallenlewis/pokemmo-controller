"""A Steam account whose shortcuts.vdf is an empty file when PokeMMO Controller is installed.

The install keeps that empty file as the backup. An empty file holds no shortcuts: later runs must
read the backup that way, not refuse it as unreadable (which used to stop a rerun from putting the
PokeMMO shortcut back, and made uninstall leave the shortcut behind or stop with an error once Steam
had rewritten the file).
"""
import unittest

from helpers import GAME, Sandbox
import install_wheel as W

USER = "userdata/12345/config/shortcuts.vdf"


def pokemmo_count(data):
    return sum(1 for v in W.read_shortcuts(data).values() if W.is_pokemmo_shortcut(v))


class EmptyShortcutsFile(unittest.TestCase):
    def make(self):
        sb = Sandbox()
        self.addCleanup(sb.cleanup)
        f = sb.steam / USER
        f.write_bytes(b"")
        sb.setup()
        self.assertEqual(pokemmo_count(f.read_bytes()), 1)
        return sb, f

    def steam_rewrites(self, f, change):
        sc = W.read_shortcuts(f.read_bytes())
        change(sc)
        f.write_bytes(W.write_shortcuts(sc))

    def test_rerun_reads_the_empty_backup(self):
        sb, f = self.make()
        r = sb.setup()
        self.assertNotIn("Could not read", r.stdout + r.stderr)
        self.assertEqual(pokemmo_count(f.read_bytes()), 1)

    def test_rerun_puts_back_a_shortcut_removed_in_steam(self):
        sb, f = self.make()
        self.steam_rewrites(f, lambda sc: sc.clear())
        r = sb.setup()
        self.assertNotIn("Could not read", r.stdout + r.stderr)
        self.assertEqual(pokemmo_count(f.read_bytes()), 1)

    def test_uninstall_after_the_player_added_a_game(self):
        sb, f = self.make()
        self.steam_rewrites(f, lambda sc: sc.update({"7": dict(GAME)}))
        r = sb.setup("--uninstall")
        self.assertNotIn("Could not read", r.stdout + r.stderr)
        sc = W.read_shortcuts(f.read_bytes())
        self.assertEqual(pokemmo_count(f.read_bytes()), 0)
        self.assertEqual([v.get("AppName") for v in sc.values()], [GAME["AppName"]])

    def test_uninstall_after_steam_touched_only_our_shortcut(self):
        sb, f = self.make()

        def played(sc):
            for v in sc.values():
                if W.is_pokemmo_shortcut(v):
                    v["LastPlayTime"] = 1700000001
        self.steam_rewrites(f, played)
        r = sb.setup("--uninstall")
        self.assertNotIn("Could not read", r.stdout + r.stderr)
        self.assertEqual(f.read_bytes(), b"")   # the file is as it was before the install


if __name__ == "__main__":
    unittest.main()
