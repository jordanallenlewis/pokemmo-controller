"""Pad names and the button-map art: every family names every input the layout can
use, and the generated pictures match the default layout (so they cannot drift)."""
import subprocess, sys, unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import layout as L  # noqa: E402
import pads  # noqa: E402


class Pads(unittest.TestCase):
    def test_every_family_names_every_button_and_axis(self):
        for fam in pads.FAMILIES:
            for b in range(L.BUTTONS):
                self.assertTrue(pads.button_label(fam, b), (fam, b))
            for a in range(L.AXES):
                for pos in (False, True):
                    self.assertTrue(pads.axis_label(fam, a, pos), (fam, a, pos))

    def test_known_names(self):
        self.assertEqual(pads.button_label("xbox", 0), "A")
        self.assertEqual(pads.button_label("playstation", 0), "Cross")
        self.assertEqual(pads.button_label("switch", 0), "B")   # bottom button is B on a Switch pad
        self.assertEqual(pads.button_label("switch", 1), "A")
        self.assertEqual(pads.axis_label("playstation", 5, True), "R2")
        self.assertEqual(pads.axis_label("xbox", 1, False), "Left stick up")

    def test_each_default_action_has_a_name_per_family(self):
        for fam in pads.FAMILIES:
            rows = pads.describe(L.default_layout(), fam)
            self.assertEqual({r[0] for r in rows}, set(L.ACTIONS))
            self.assertTrue(all(r[2] for r in rows))

    def test_inputs_in_a_layout_are_not_confused(self):
        # two different inputs never share a printed name inside one family
        for fam in pads.FAMILIES:
            names = [pads.button_label(fam, b) for b in range(L.BUTTONS)]
            self.assertEqual(len(names), len(set(names)), fam)

    def test_art_is_valid_svg_and_shows_every_action(self):
        for fam in ("playstation", "switch"):
            svg = pads.render_svg(L.default_layout(), fam)
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"))
            text = " ".join(root.itertext())
            for label in L.ACTIONS.values():
                self.assertIn(label, text, (fam, label))
            for w in L.WHEEL_ACTIONS.values():
                self.assertIn(w[1], text, (fam, w[1]))
            self.assertNotIn("<script", svg)
            self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))

    def test_committed_art_matches_the_generator(self):
        for fam in ("playstation", "switch"):
            f = ROOT / "docs" / f"button-map-{fam}.svg"
            self.assertTrue(f.exists(), f)
            self.assertEqual(f.read_text(encoding="utf-8").replace("\r\n", "\n"),
                             pads.render_svg(L.default_layout(), fam))

    def test_cli_prints_a_table(self):
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "pads.py"), "playstation"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Cross", out.stdout)
        self.assertIn("Focus Ring", out.stdout)


if __name__ == "__main__":
    unittest.main()
