"""One source of truth: tools/layout.py (with site/data/hotspots.json for the photos). Every generated copy
(site/data/layout.json, the README tables) must be what site/build.py writes today, and nothing restates
the layout by hand."""
import importlib.util, re, unittest
from pathlib import Path

import helpers  # noqa: F401
import layout as L

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("site_build", ROOT / "site" / "build.py")
site_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_build)


class Canon(unittest.TestCase):
    def test_generated_copies_are_current(self):
        for path, text in site_build.outputs().items():
            cur = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
            self.assertEqual(cur, text, f"{Path(path).name} is stale: run python site/build.py")

    def test_readme_tables_hold_every_default_action_for_every_pad(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for kind in L.PAD_ORDER:
            block = re.search(rf"<!-- generated:map-{kind} -->\n(.*?)\n<!-- /generated -->", readme, re.S).group(1)
            for part, label in L.part_controls(L.default_layout(), kind).items():
                self.assertIn(f"| {L.part_names(kind)[part]} | {label} |", block, (kind, part))

    def test_switch_confirm_is_the_printed_a(self):
        c, n = L.part_controls(L.default_layout(), "switch"), L.part_names("switch")
        self.assertEqual(n["b"], "A")                      # the right-hand button is printed A
        self.assertEqual(c["b"], "Confirm / interact")     # and it confirms (the website used to show B)
        self.assertEqual(L.part_controls(L.default_layout(), "xbox")["a"], "Confirm / interact")

    def test_nothing_restates_names_by_hand(self):
        js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("MODELS", js)
        self.assertNotIn('"Left stick"', js)
        self.assertNotIn("Triangle", js)
        for rel in ("tools/pads.py", "site/build.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn('"Cross"', text, rel)
            self.assertNotIn('"Circle"', text, rel)

    def test_the_app_draws_the_photo_not_an_outline(self):
        page = (ROOT / "tools" / "ui_page.html").read_text(encoding="utf-8")
        self.assertIn("const PADPHOTOS = {", page)
        self.assertIn('sv("image", {class: "photo"', page)
        self.assertNotIn('class: "body"', page)       # the old drawn outline
        self.assertNotIn('class: "deco"', page)
        for kind in ("xbox", "playstation", "switch"):
            self.assertIn(f'"{kind}":{{"img":"data:image/webp;base64,', page)

    def test_every_pad_names_every_input(self):
        for kind in L.PAD_ORDER:
            self.assertEqual(len(L.PADS[kind]["buttons"]), L.BUTTONS)
            self.assertEqual(len(L.PADS[kind]["axes"]), L.AXES)
            self.assertEqual(len(set(L.PADS[kind]["buttons"])), L.BUTTONS, kind)


if __name__ == "__main__":
    unittest.main()
