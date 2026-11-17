"""The game's resolution can change while it is played: 4K down to 1080p, up to 1440p, back, in
fullscreen, borderless or a window, between monitors, at another display scale, with the game
window briefly reporting 0x0 or half a size. The wheel has to follow and stay on screen."""
import itertools, random, re, subprocess, sys, tempfile, time, unittest
from pathlib import Path

from helpers import Sandbox, TOOLS
import fit
import layout as L
import platforms as P
from test_setup import Base

BAD = [(0, 0), (0, 1080), (1920, 0), (-1, -1), (1, 1), (160, 28), (None, None), ("1920", "1080"),
       (1920.5, 1080), (True, True), (99999, 99999), (3840, 40), (40, 2160), (), (1920,), None, "1080p"]


def fed(f, samples):
    return [f.feed(s) for s in samples]


class Debounce(unittest.TestCase):
    def test_a_sequence_of_changes_is_followed_in_any_order(self):
        sizes = [(3840, 2160), (1920, 1080), (2560, 1440), (3840, 2160), (1280, 720), (2560, 1440), (1920, 1080)]
        f = fit.Follower(applied=None)
        for size in sizes:
            got = [x for x in fed(f, [size] * fit.SETTLE) if x]
            want = L.wheel_scale(*size)
            # the wheel is written once per real change of its size, and fits after every change
            self.assertEqual(f.scale, want, size)
            self.assertTrue(fit.fits(f.scale, *size), size)
            self.assertLessEqual(len(got), 1)

    def test_junk_samples_never_change_the_size_and_never_raise(self):
        f = fit.Follower(applied=(1920, 1080))
        for _ in range(3):
            for bad in BAD:
                self.assertIsNone(f.feed(bad), bad)
        self.assertEqual(f.scale, L.wheel_scale(1920, 1080))

    def test_zero_size_in_the_middle_of_a_switch(self):
        f = fit.Follower(applied=(3840, 2160))
        out = fed(f, [(3840, 2160), (0, 0), (1920, 1080), (0, 0), (1920, 1080), (1, 1), (1920, 1080)])
        self.assertEqual([x for x in out if x], [(1920, 1080)])
        self.assertEqual(f.scale, 200)

    def test_rapid_flicker_does_not_write_and_the_last_stable_size_wins(self):
        f = fit.Follower(applied=(3840, 2160))
        flicker = [(1920, 1080), (2560, 1440)] * 10
        self.assertEqual([x for x in fed(f, flicker) if x], [])
        self.assertEqual(f.scale, 400)
        self.assertEqual([x for x in fed(f, [(1280, 720)] * 5) if x], [(1280, 720)])
        self.assertEqual(f.scale, L.wheel_scale(1280, 720))

    def test_a_move_between_monitors_of_the_same_size_writes_nothing(self):
        f = fit.Follower(applied=(2560, 1440))
        self.assertEqual([x for x in fed(f, [(2560, 1440)] * 6 + [(2560, 1444)] * 6) if x], [])

    def test_the_login_window_is_not_a_game_picture(self):
        # real hardware: every launch passes a 640x480 login window, before and after the real size
        f = fit.Follower(applied=(2560, 1440))
        self.assertEqual([x for x in fed(f, [(640, 480)] * 20) if x], [])
        self.assertEqual(f.scale, L.wheel_scale(2560, 1440))
        self.assertIsNone(fit.sanitize((640, 480)))
        self.assertEqual([x for x in fed(f, [(1920, 1080)] * fit.SETTLE) if x], [(1920, 1080)])

    def test_a_minimized_game_reading_nothing_keeps_the_last_size(self):
        f = fit.Follower(applied=(2560, 1440))
        self.assertEqual([x for x in fed(f, [None] * 20) if x], [])
        self.assertEqual(f.scale, L.wheel_scale(2560, 1440))

    def test_a_tiny_scale_difference_between_monitors_writes_nothing(self):
        # real hardware: 2536x1376 -> 2544x1401 (another display scale) gave 255 -> 259
        f = fit.Follower(applied=(2536, 1376))
        self.assertEqual(f.scale, 255)
        self.assertEqual([x for x in fed(f, [(2544, 1401)] * 6) if x], [])
        self.assertEqual(f.scale, 255)
        # a bigger change still writes, and a wheel that would no longer fit is rewritten
        self.assertEqual([x for x in fed(f, [(1920, 1080)] * 4) if x], [(1920, 1080)])
        g = fit.Follower(applied=(2544, 1401))
        self.assertEqual(g.scale, 259)
        self.assertFalse(fit.fits(259, 2536, 1376))       # too big for the smaller picture: rewritten
        self.assertEqual([x for x in fed(g, [(2536, 1376)] * 4) if x], [(2536, 1376)])

    def test_windowed_resize_drag_ends_on_the_final_size(self):
        f = fit.Follower(applied=(1920, 1080))
        drag = [(1920 - i * 40, 1080 - i * 22) for i in range(1, 25)]
        fed(f, drag)
        end = drag[-1]
        fed(f, [end] * fit.SETTLE)
        self.assertEqual(f.scale, L.wheel_scale(*end))

    def test_random_storms_always_end_on_the_last_stable_size_and_fit(self):
        rng = random.Random(7)
        pool = [(3840, 2160), (1920, 1080), (2560, 1440), (1280, 720), (3440, 1440), (1024, 768), (7680, 4320), (800, 600)]
        for round_ in range(200):
            f = fit.Follower(applied=rng.choice(pool))
            last = None
            for _ in range(rng.randint(1, 12)):
                size = rng.choice(pool)
                for _ in range(rng.randint(1, 8)):
                    fed(f, [size] if rng.random() > 0.3 else [rng.choice(BAD)])
                    if f._n >= fit.SETTLE:
                        last = size
                if f._cand and f._n >= fit.SETTLE:
                    self.assertEqual(f.scale, L.wheel_scale(*f._cand))
                    self.assertTrue(fit.fits(f.scale, *f._cand))

    def test_a_failed_write_is_tried_again(self):
        calls = []

        def apply(size):
            calls.append(size)
            if len(calls) == 1:
                raise OSError("busy")

        seq = iter([(1920, 1080)] * 12)
        done = fit.follow(lambda: next(seq), apply, sleep=lambda s: None, applied=(3840, 2160), limit=12, say=lambda m: None)
        self.assertEqual(calls, [(1920, 1080)] * 2)
        self.assertEqual(done, [(1920, 1080)])

    def test_a_reader_that_raises_is_survived(self):
        def read():
            raise RuntimeError("display query failed")
        self.assertEqual(fit.follow(read, lambda s: 1 / 0, sleep=lambda s: None, limit=5, say=lambda m: None), [])

    def test_bounds_after_every_size_on_a_grid(self):
        for w, h in itertools.product(range(320, 8200, 280), range(320, 4400, 240)):
            if max(w, h) > fit.MAX_ASPECT * min(w, h):
                self.assertIsNone(fit.sanitize((w, h)))
                continue
            self.assertEqual(fit.sanitize((w, h)), (w, h))
            self.assertTrue(fit.fits(L.wheel_scale(w, h), w, h), (w, h))


class Detection(unittest.TestCase):
    def test_xrandr_prefers_the_primary(self):
        t = ("Screen 0: minimum 8 x 8, current 5760 x 2160, maximum 32767 x 32767\n"
             "HDMI-1 connected 1920x1080+3840+0 (normal left inverted right x axis y axis) 530mm x 300mm\n"
             "   1920x1080     60.00*+\n"
             "DP-1 connected primary 3840x2160+0+0 (normal left) 600mm x 340mm\n"
             "DP-2 disconnected (normal left)\n")
        self.assertEqual(P.parse_xrandr(t), (3840, 2160))
        self.assertEqual(P.parse_xrandr(t.replace(" primary", "")), (1920, 1080))
        self.assertIsNone(P.parse_xrandr(""))
        self.assertIsNone(P.parse_xrandr("DP-1 disconnected\n"))

    def test_xwininfo(self):
        self.assertEqual(P.parse_xwininfo("  Width: 1600\n  Height: 900\n  Depth: 24\n"), (1600, 900))
        self.assertIsNone(P.parse_xwininfo("xwininfo: error: No such window"))

    def test_system_profiler(self):
        j = ('{"SPDisplaysDataType":[{"spdisplays_ndrvs":['
             '{"_spdisplays_pixels":"1920 x 1080","spdisplays_main":"spdisplays_no"},'
             '{"_spdisplays_pixels":"5120 x 2880","spdisplays_main":"spdisplays_yes"}]}]}')
        self.assertEqual(P.parse_system_profiler(j), (5120, 2880))
        for bad in ("", "{}", "[]", "null", '{"SPDisplaysDataType":[1,{"spdisplays_ndrvs":[2]}]}'):
            try:
                self.assertIsNone(P.parse_system_profiler(bad))
            except AttributeError:
                self.fail(f"raised on {bad!r}")


class Following(Base):
    """setup.py --follow against a sandbox: the screen is a file the test rewrites."""

    def scales(self, sb):
        found = set()
        for f in (sb.cfg / "pokemmo").glob("controller_*.vdf"):
            for _ in range(50):      # Windows refuses a read while the file is being swapped in
                try:
                    text = f.read_text()
                    break
                except OSError:
                    time.sleep(0.02)
            else:
                raise AssertionError(f"could not read {f}")
            found.add(int(re.search(r'"touch_menu_scale"\t\t"(\d+)"', text).group(1)))
        return found

    def wait_for(self, sb, want, secs=40):
        end = time.time() + secs
        while time.time() < end:
            if self.scales(sb) == {want}:
                return True
            time.sleep(0.05)
        return False

    def test_follow_through_a_session_of_resolution_changes(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        screen = Path(td.name) / "screen.txt"
        self.last = (3840, 2160)
        screen.write_text("3840x2160")
        cmd = [sys.executable, str(TOOLS / "setup.py"), "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam),
               "--follow", "--follow-interval", "0.05"]
        proc = subprocess.Popen(cmd, env=sb.env(POKEMMO_CONTROLLER_TEST_SIZE_FILE=str(screen),
                                                POKEMMO_CONTROLLER_TEST_POLLS="2000"),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            session = ["1920x1080", "0x0", "2560x1440", "1x1", "3840x2160", "1280x720", "2560x1440", "1920x1080"]
            for text in session:
                screen.write_text(text)
                w, h = map(int, text.split("x"))
                if fit.sanitize((w, h)) is None:
                    time.sleep(0.4)          # junk: whatever was there stays
                    self.assertTrue(self.scales(sb) <= {L.wheel_scale(*self.last)}, (text, self.scales(sb)))
                    continue
                self.last = (w, h)
                self.assertTrue(self.wait_for(sb, L.wheel_scale(w, h)), f"{text}: {self.scales(sb)}")
                self.assertTrue(fit.fits(L.wheel_scale(w, h), w, h))
        finally:
            time.sleep(0.5)          # nothing is being written: the size is stable
            proc.terminate()
            proc.wait(timeout=20)
        # the following only ever touched the wheel files; uninstall still puts back every byte
        sb.setup("--uninstall")
        self.assertSame(before, sb.snapshot())

    def test_follow_before_install_says_so(self):
        sb = self.make()
        r = sb.setup("--follow", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not installed", r.stdout + r.stderr)

    def test_follow_refuses_other_options(self):
        sb = self.make()
        r = sb.setup("--follow", "--uninstall", check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
