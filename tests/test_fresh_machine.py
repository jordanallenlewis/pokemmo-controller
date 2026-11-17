"""A fresh machine: PokeMMO only (no Steam, no Python on the user's side beyond the installer's own),
and a clean install/uninstall round trip that leaves nothing behind."""
import unittest

from helpers import Sandbox


class NoSteam(unittest.TestCase):
    def test_install_without_steam_writes_native_binds_only(self):
        sb = Sandbox(steam=False)
        self.addCleanup(sb.cleanup)
        before = sb.snapshot()
        r = sb.setup(steam=False)
        self.assertIn("without the wheel", r.stdout)
        self.assertIn("Start PokeMMO and play", r.stdout)
        self.assertNotIn("Launch PokeMMO from your Steam library", r.stdout)
        props = sb.props.read_text(encoding="utf-8")
        self.assertIn("client.controls.controller_input_maps_gdx_2=", props)
        self.assertIn("Xbox One S Controller", props)
        self.assertIn("Logitech Dual Action", props)  # the player's own map is kept
        self.assertFalse((sb.root / "Steam").exists())  # no Steam folder invented

    def test_no_steam_uninstall_restores_every_byte(self):
        sb = Sandbox(steam=False)
        self.addCleanup(sb.cleanup)
        before = sb.snapshot()
        sb.setup(steam=False)
        self.assertNotEqual(sb.snapshot(), before)
        sb.setup("--uninstall", steam=False)
        self.assertEqual(sb.snapshot(), before)

    def test_no_steam_reinstall_is_a_no_op(self):
        sb = Sandbox(steam=False)
        self.addCleanup(sb.cleanup)
        sb.setup(steam=False)
        once = sb.snapshot()
        r = sb.setup(steam=False)
        self.assertIn("Already up to date", r.stdout)
        self.assertEqual(sb.snapshot(), once)


class FreshMachine(unittest.TestCase):
    def test_install_then_uninstall_with_steam_restores_every_byte(self):
        sb = Sandbox()
        self.addCleanup(sb.cleanup)
        before = sb.snapshot()
        sb.setup()
        sb.setup("--uninstall")
        self.assertEqual(sb.snapshot(), before)

    def test_never_started_game_gets_a_plain_message_and_no_changes(self):
        sb = Sandbox(props=None, steam=False)
        self.addCleanup(sb.cleanup)
        before = sb.snapshot()
        r = sb.setup(steam=False, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Start PokeMMO once, close it, try again", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(sb.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
