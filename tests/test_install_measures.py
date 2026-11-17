"""The installer measures the game's picture itself: a player on a 1080p screen must get a wheel
that fits without running --resolution or --follow (real report, 2026-11-17: the wheel came out
4K-sized, off screen, because nothing at install time looked at the screen)."""
import re, tempfile, unittest
from pathlib import Path

from helpers import TOOLS  # noqa: F401  (puts tools/ on the path)
import layout as L
from test_setup import Base


def scales(sb):
    return {int(re.search(r'"touch_menu_scale"\t\t"(\d+)"', f.read_text()).group(1))
            for f in (sb.cfg / "pokemmo").glob("controller_*.vdf")}


class InstallMeasures(Base):
    def screen(self, text):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        f = Path(td.name) / "screen.txt"
        f.write_text(text)
        return {"POKEMMO_CONTROLLER_TEST_SIZE_FILE": str(f)}

    def test_install_sizes_the_wheel_for_the_screen(self):
        sb = self.make()
        sb.setup(env=self.screen("1920x1080"))
        self.assertEqual(scales(sb), {L.wheel_scale(1920, 1080)})

    def test_an_explicit_resolution_wins_over_the_measurement(self):
        sb = self.make()
        sb.setup("--resolution", "2560x1440", env=self.screen("1920x1080"))
        self.assertEqual(scales(sb), {L.wheel_scale(2560, 1440)})

    def test_a_4k_screen_leaves_the_default_and_no_trace(self):
        sb = self.make()
        sb.setup(env=self.screen("3840x2160"))
        self.assertEqual(scales(sb), {400})

    def test_an_unreadable_screen_keeps_the_default(self):
        sb = self.make()
        sb.setup(env=self.screen("nonsense"))
        self.assertEqual(scales(sb), {400})

    def test_rerun_remeasures_unless_the_player_chose_a_size(self):
        sb = self.make()
        sb.setup(env=self.screen("1920x1080"))
        sb.setup(env=self.screen("2560x1440"))
        self.assertEqual(scales(sb), {L.wheel_scale(2560, 1440)})
        sb.setup("--resolution", "1280x720", env=self.screen("2560x1440"))
        sb.setup(env=self.screen("1920x1080"))      # chosen by hand: kept
        self.assertEqual(scales(sb), {L.wheel_scale(1280, 720)})

    def test_uninstall_after_a_measured_install_restores_every_byte(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup(env=self.screen("1920x1080"))
        sb.setup("--uninstall")
        self.assertSame(before, sb.snapshot())




class RealDisplay(unittest.TestCase):
    """The one test that asks this machine's real display (every CI leg runs it): the question
    must never raise, and what it answers must be a picture size or nothing."""

    def test_reading_the_real_screen_is_safe(self):
        import platforms as P
        from unittest import mock
        with mock.patch.object(P, "TEST", False):
            got = P.game_size()
        self.assertTrue(got is None or (len(got) == 2 and all(isinstance(v, int) for v in got)), got)


if __name__ == "__main__":
    unittest.main()
