"""The wheel is drawn by Steam in screen pixels, so its size follows the game picture:
a 4K-sized wheel ran off a lower-resolution screen. Every common size, shape and
change of mind has to give a wheel that fits and a clean install, rerun and uninstall."""
import re, unittest

from helpers import Sandbox
import layout as L
import install_wheel
from test_setup import Base, diff

SIZES = [  # (w, h, expected Steam size)
    (1280, 720, 133), (1366, 768, 142), (1600, 900, 167), (1920, 1080, 200),
    (2560, 1440, 267), (3840, 2160, 400),
    (7680, 4320, 400),            # above 4K: never bigger than the 4K size
    (3440, 1440, 267), (2560, 1080, 200), (5120, 1440, 267), (3840, 1600, 296),   # ultrawide
    (1024, 768, 142), (1600, 1200, 222), (1280, 1024, 190),                        # 4:3 and 5:4
    (800, 600, 111), (640, 480, 89),                                               # small windows
    (1080, 1920, 200),               # a tall window: the short side counts
    (320, 320, 60),                  # never below a readable wheel
]


def scale_in(vdf):
    return int(re.search(r'"touch_menu_scale"\t\t"(\d+)"', vdf).group(1))


class Sizing(unittest.TestCase):
    def test_table(self):
        for w, h, want in SIZES:
            with self.subTest(size=f"{w}x{h}"):
                self.assertEqual(L.wheel_scale(w, h), want)

    def test_never_bigger_than_the_4k_wheel_and_grows_with_height(self):
        last = 0
        for h in range(320, 9000, 40):
            s = L.wheel_scale(h * 16 // 9, h)
            self.assertTrue(L.MIN_WHEEL_SCALE <= s <= 400)
            self.assertGreaterEqual(s, last)
            last = s

    def test_the_wheel_fits_the_screen_at_every_size(self):
        # the wheel is about 400-scale = (short side) in the 4K design: its share of the
        # short side never exceeds what a 4K player gets, unless it hit the readable floor
        for w, h, _ in SIZES:
            share = L.wheel_scale(w, h) / min(w, h)
            if L.wheel_scale(w, h) > L.MIN_WHEEL_SCALE:
                self.assertLessEqual(share, 400 / 2160 + 0.001, f"{w}x{h}")

    def test_parse(self):
        for text in ("1920x1080", "1920 x 1080", "1920X1080", "1920*1080", "1920,1080", " 1920x1080 "):
            self.assertEqual(L.parse_resolution(text), (1920, 1080))

    def test_refuses_nonsense(self):
        for bad in ("", "big", "1080p", "0x0", "100x100", "99999x99999", "-1920x1080", "1920x", "1920x1080x2",
                    "1e3x1e3", "1920x1080; rm"):
            with self.subTest(bad=bad), self.assertRaises(L.LayoutError):
                L.parse_resolution(bad)
        for bad in ((True, 1080), (1920.5, 1080), ("1920", "1080")):
            with self.assertRaises(L.LayoutError):
                L.check_resolution(*bad)

    def test_a_record_edited_by_hand_is_ignored(self):
        for junk in ("big", [1], [1, 2, 3], [10, 10], ["a", "b"], None, {"w": 1}, [True, True]):
            self.assertIsNone(L.recorded_screen({"screen": junk}))

    def test_default_build_is_unchanged(self):
        self.assertEqual(scale_in(install_wheel.build_layout("controller_xboxone")), 400)


class Installed(Base):
    def vdfs(self, sb):
        return {f.name: scale_in(f.read_text()) for f in (sb.cfg / "pokemmo").glob("controller_*.vdf")}

    def test_resolution_install_rerun_update_uninstall(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--resolution", "1920x1080")
        self.assertIn("Installed", r.stdout)
        self.assertIn("1920x1080", r.stdout)
        sizes = self.vdfs(sb)
        self.assertTrue(sizes and set(sizes.values()) == {200}, sizes)   # every pad type
        installed = sb.snapshot()
        # rerun with the same size and with no flag: nothing changes, the size is kept
        self.assertEqual(diff(installed, sb.snapshot()), [])
        self.assertIn("Already up to date", sb.setup("--resolution", "1920x1080").stdout)
        self.assertIn("Already up to date", sb.setup().stdout)
        self.assertEqual(diff(installed, sb.snapshot()), [])
        # the player turns the game resolution down further: only the wheel files change
        sb.setup("--resolution", "1280x720")
        self.assertEqual(set(self.vdfs(sb).values()), {133})
        # back to 4K (or reset): the default wheel again, no record of a size
        sb.setup("--resolution", "3840x2160")
        self.assertEqual(set(self.vdfs(sb).values()), {400})
        sb.setup("--resolution", "1920x1080")
        sb.setup("--reset-resolution")
        self.assertEqual(set(self.vdfs(sb).values()), {400})
        # uninstall puts back every byte
        sb.setup("--resolution", "1024x768")
        sb.setup("--uninstall")
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_default_install_has_no_trace_of_a_size(self):
        sb = self.make()
        sb.setup()
        self.assertEqual(set(self.vdfs(sb).values()), {400})
        sb.setup("--resolution", "3840x2160")
        self.assertNotIn("screen", (sb.pokemmo / "config" / "pokemmo-controller.json").read_text())

    def test_bad_resolution_changes_nothing(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--resolution", "huge", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Write it like 1920x1080", r.stdout + r.stderr)
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_size_does_not_touch_the_binds_or_the_wheel_slices(self):
        a, b = self.make(), self.make()
        a.setup()
        b.setup("--resolution", "1280x720")
        self.assertEqual(a.props.read_bytes(), b.props.read_bytes())
        va = (a.cfg / "pokemmo" / "controller_xboxone.vdf").read_text()
        vb = (b.cfg / "pokemmo" / "controller_xboxone.vdf").read_text()
        self.assertEqual(va.replace('"400"', '"133"'), vb)   # one value differs, nothing else

    def test_no_wheel_install_takes_the_flag_without_error(self):
        sb = self.make()
        self.assertIn("Installed", sb.setup("--resolution", "1920x1080", "--no-wheel").stdout)


if __name__ == "__main__":
    unittest.main()
