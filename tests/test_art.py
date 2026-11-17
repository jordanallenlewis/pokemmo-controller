"""The README's pictures. Banners (docs/img/*.svg) are written by docs/art/build.py and must be what it
writes today; the controller maps and the wheel (docs/img/*.png) are screenshots of the website's map made
from real photos by docs/art/render.py, and must match what they are made from. No picture may draw a
controller: the only controller images are the photos."""
import importlib.util, json, re, tempfile, unittest
from pathlib import Path

import helpers  # noqa: F401
import layout as L

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "img"


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = load("art_build", "docs/art/build.py")
render = load("art_render", "docs/art/render.py")


class Banners(unittest.TestCase):
    def test_committed_banners_are_what_the_script_writes(self):
        with tempfile.TemporaryDirectory() as td:
            build.main(td)
            made = sorted(p.name for p in Path(td).iterdir())
            have = sorted(p.name for p in IMG.glob("*.svg"))
            self.assertEqual(made, have)
            for n in made:
                self.assertEqual((Path(td) / n).read_text(encoding="utf-8"),
                                 (IMG / n).read_text(encoding="utf-8").replace("\r\n", "\n"), n)

    def test_every_banner_has_a_light_and_a_dark_variant(self):
        names = {p.name for p in IMG.glob("*.svg")}
        for n in names:
            base, theme = re.match(r"(.+)-(light|dark)\.svg$", n).groups()
            self.assertIn(f"{base}-{'dark' if theme == 'light' else 'light'}.svg", names)

    def test_readme_uses_each_picture_in_both_themes_and_describes_it(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for p in list(IMG.glob("*-light.svg")) + list(IMG.glob("*-light.png")):
            base, ext = p.name[:-len("-light" + p.suffix)], p.suffix
            self.assertIn(f"docs/img/{base}-light{ext}", readme, base)
            self.assertIn(f"docs/img/{base}-dark{ext}", readme, base)
        for img in re.findall(r"<img [^>]*>", readme):
            self.assertRegex(img, r'alt="[^"]+"')

    def test_banners_carry_no_credit_lines(self):
        for p in IMG.glob("*.svg"):
            text = p.read_text(encoding="utf-8")
            for bad in ("Trinity", "Claude", "agent"):
                self.assertNotIn(bad, text, p.name)

    def test_text_in_the_banners_is_readable_in_both_themes(self):
        def lum(h):
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
            f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
        def ratio(a, b):
            x, y = sorted((lum(a), lum(b)), reverse=True)
            return (x + 0.05) / (y + 0.05)
        for t, c in build.THEMES.items():
            for fg, bgk in (("ink", "bg"), ("ink", "card"), ("mute", "card"), ("mute", "bg"), ("accent", "card"),
                            ("accent", "soft"), ("on", "fill")):
                self.assertGreaterEqual(ratio(c[fg], c[bgk]), 4.5, f"{t}: {fg} on {bgk}")


class Maps(unittest.TestCase):
    def test_maps_match_what_they_are_made_from(self):
        self.assertEqual(render.check(), [])

    def test_a_changed_default_makes_the_check_fail(self):
        before = render.fingerprint()
        f = ROOT / "site" / "data" / "layout.json"
        orig = f.read_bytes()
        try:
            f.write_bytes(orig.replace(b'"Bag"', b'"Backpack"', 1))
            self.assertNotEqual(render.fingerprint(), before)
        finally:
            f.write_bytes(orig)

    def test_no_picture_draws_a_controller_or_the_wheel(self):
        self.assertEqual(sorted(p.name for p in IMG.glob("map-*.svg")) + sorted(p.name for p in IMG.glob("wheel*.svg")), [])
        self.assertFalse((ROOT / "docs" / "button-map-playstation.svg").exists())
        self.assertFalse((ROOT / "docs" / "button-map-switch.svg").exists())
        src = (ROOT / "docs" / "art" / "build.py").read_text(encoding="utf-8")
        for word in ("body_gamepad", "pad_art", "button_map", "wheel_group"):
            self.assertNotIn(word, src)

    def test_every_pad_has_a_photo_and_a_spot_for_every_part_the_layout_shows(self):
        hot = json.loads((ROOT / "site" / "data" / "hotspots.json").read_text(encoding="utf-8"))["pads"]
        self.assertEqual(set(hot), set(L.PAD_ORDER))
        for kind in L.PAD_ORDER:
            self.assertTrue((ROOT / hot[kind]["photo"]).exists(), kind)
            parts = {p.replace("_click", "") for p in L.part_controls(L.default_layout(), kind)}
            self.assertLessEqual(parts, set(hot[kind]["spots"]), kind)


if __name__ == "__main__":
    unittest.main()
