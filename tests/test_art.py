"""The README's pictures are drawn by docs/art/build.py. They must be what the script
draws today, come in a light and a dark variant, and say what the default layout does."""
import importlib.util, re, tempfile, unittest
from pathlib import Path

import helpers  # noqa: F401
import layout as L

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("art_build", ROOT / "docs" / "art" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def fold(s):
    return s.replace("é", "e")


class Art(unittest.TestCase):
    def test_committed_pictures_are_what_the_script_draws(self):
        with tempfile.TemporaryDirectory() as td:
            build.main(td)
            made = sorted(p.name for p in Path(td).iterdir())
            have = sorted(p.name for p in (ROOT / "docs" / "img").iterdir())
            self.assertEqual(made, have)
            for n in made:
                self.assertEqual((Path(td) / n).read_text(encoding="utf-8"),
                                 (ROOT / "docs" / "img" / n).read_text(encoding="utf-8").replace("\r\n", "\n"), n)

    def test_every_picture_has_a_light_and_a_dark_variant(self):
        names = {p.name for p in (ROOT / "docs" / "img").iterdir()}
        for n in names:
            base, theme = re.match(r"(.+)-(light|dark)\.svg$", n).groups()
            self.assertIn(f"{base}-{'dark' if theme == 'light' else 'light'}.svg", names)

    def test_readme_uses_each_picture_in_both_themes_and_describes_it(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for p in (ROOT / "docs" / "img").glob("*-light.svg"):
            base = p.name[:-len("-light.svg")]
            self.assertIn(f"docs/img/{base}-light.svg", readme, base)
            self.assertIn(f"docs/img/{base}-dark.svg", readme, base)
        for img in re.findall(r"<img [^>]*>", readme):
            self.assertRegex(img, r'alt="[^"]+"')

    def test_wheel_picture_matches_the_wheel(self):
        self.assertEqual([k for k, _ in build.WHEEL], [v[0] for v in L.WHEEL_ACTIONS.values()])
        self.assertEqual([fold(n) for _, n in build.WHEEL], [v[1] for v in L.WHEEL_ACTIONS.values()])

    def test_maps_name_the_default_hotbar_and_menu_actions(self):
        b = L.DEFAULT_BINDS
        self.assertEqual(b["KEY_HOTBAR_5"], {"button": 4})            # View: the map slot
        self.assertEqual(b["KEY_RING_FOCUS"], {"button": 9})          # LB: Focus Ring
        self.assertEqual([b[f"KEY_HOTBAR_{n}"] for n in (1, 2, 3, 4)],
                         [{"button": 11}, {"button": 14}, {"button": 12}, {"button": 13}])
        for k, cfg in build.PADS.items():
            svg = build.button_map("light", k)
            for word in (cfg["view"], cfg["lb"], "Focus Ring", "Map", "Hotbar 1 / 2", "Hotbar 3 / 4", "Wheel"):
                self.assertIn(f">{word}<", svg, f"{k}: {word}")

    def test_no_one_input_is_drawn_doing_two_things(self):
        for k in build.PADS:
            svg = build.button_map("light", k)
            for chip in re.findall(r'letter-spacing="\.6">([^<]+)<', svg):
                self.assertEqual(svg.count(f'letter-spacing=".6">{chip}<'), 1, f"{k}: {chip} twice")

    def test_pictures_carry_no_brand_art_or_credit_lines(self):
        for p in (ROOT / "docs" / "img").iterdir():
            text = p.read_text(encoding="utf-8")
            for bad in ("Trinity", "Claude", "agent", "<image", "base64"):
                self.assertNotIn(bad, text, p.name)


if __name__ == "__main__":
    unittest.main()
