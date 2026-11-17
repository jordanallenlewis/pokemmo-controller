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
        # the bottom button is printed B on a Switch pad (positional = the physical button)
        self.assertEqual(pads.button_label("switch", 0, switch_positional=True), "B")
        self.assertEqual(pads.button_label("switch", 1, switch_positional=True), "A")
        # by default the confirm action follows the printed A (the face buttons swap in pairs)
        self.assertEqual(pads.button_label("switch", 0), "A")
        self.assertEqual(pads.button_label("switch", 1), "B")
        self.assertEqual(pads.axis_label("playstation", 5, True), "R2")
        self.assertEqual(pads.axis_label("xbox", 1, False), "Left stick up")

    def test_switch_names_follow_the_switch_setting(self):
        # Default: the printed A confirms (like on a Switch). --switch-positional: the bottom
        # button (printed B) confirms, like Xbox. The names must say what the game will do.
        face = {r[0]: r[2] for r in pads.describe(L.default_layout(), "switch")}
        self.assertEqual([face[a] for a in ("KEY_A", "KEY_B", "KEY_X", "KEY_Y")], ["A", "B", "X", "Y"])
        pos = {r[0]: r[2] for r in pads.describe(L.default_layout(), "switch", switch_positional=True)}
        self.assertEqual([pos[a] for a in ("KEY_A", "KEY_B", "KEY_X", "KEY_Y")], ["B", "A", "Y", "X"])

    def test_switch_names_match_the_button_the_writer_uses(self):
        # tie the names to apply_native: the printed name of the button actually written
        # for a Nintendo pad is the name pads.py shows, for every button, in both settings
        import apply_native
        for positional in (False, True):
            for n in range(L.BUTTONS):
                lay = {"format": L.FORMAT, "binds": {"KEY_A": {"button": n}}, "wheel": list(L.WHEEL_ACTIONS)}
                entry = apply_native.encode_one("Nintendo Switch Pro Controller", not positional,
                                                L.native_binds(lay))
                written = int(entry.split("KEY_A,BUTTON,")[1].split(";")[0])
                self.assertEqual(pads.button_label("switch", n, switch_positional=positional),
                                 pads.button_label("switch", written, switch_positional=True), (n, positional))

    def test_unbound_actions_are_listed_not_a_crash(self):
        lay = L.default_layout()
        del lay["binds"]["KEY_TEAM"]
        L.validate(lay)
        for fam in pads.FAMILIES:
            rows = {r[0]: r[2] for r in pads.describe(lay, fam)}
            self.assertEqual(rows["KEY_TEAM"], "Not bound")
            text = " ".join(ET.fromstring(pads.render_svg(lay, fam)).itertext())
            self.assertIn("Not bound", text)
            self.assertIn("Team", text)

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

    def test_every_input_has_a_spot_and_no_text_falls_off_the_picture(self):
        # the remap screen draws any layout, not only the default: nothing may be cut off
        import random
        rng = random.Random(77)
        inputs = L.inputs()
        layouts = [{"format": L.FORMAT, "binds": {}, "wheel": list(L.WHEEL_ACTIONS)}]
        guide = L.default_layout()
        guide["binds"]["KEY_TEAM"] = {"button": 5}
        layouts.append(guide)
        for _ in range(100):
            pick = rng.sample(inputs, rng.randrange(len(L.ACTIONS) + 1))
            layouts.append({"format": L.FORMAT, "binds": dict(zip(rng.sample(list(L.ACTIONS), len(pick)), pick)),
                            "wheel": list(L.WHEEL_ACTIONS)})
        for lay in layouts:
            L.validate(lay)
            for fam in pads.FAMILIES:
                root = ET.fromstring(pads.render_svg(lay, fam))
                h = float(root.get("viewBox").split()[3])
                for t in root.iter("{http://www.w3.org/2000/svg}text"):
                    self.assertLess(float(t.get("y")), h - 8, (fam, "".join(t.itertext())))
        # the Guide / PS / Home button gets its own spot on the pad, like every other button
        svg = pads.render_svg(guide, "playstation")
        self.assertIn(">PS</text>", svg)
        for lay in layouts:
            on_pad = [b for b in lay["binds"].values() if "button" in b or b["axis"] not in (0, 1)]
            self.assertEqual(pads.render_svg(lay, "xbox").count("<circle"), len(on_pad))

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
