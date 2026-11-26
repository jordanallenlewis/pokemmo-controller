"""Cursor mode must never break 1 input = 1 action (decision 0002).

Runs over every Steam layout the installer can write. Today no layout has a cursor, so these hold
trivially; they exist so the first cursor binding cannot loosen the rule."""
import re, unittest

from helpers import TOOLS  # noqa: F401
import install_wheel

BANNED_ACTIVATORS = ("Double_Press", "Long_Press", "Start_Press", "Release", "Chord")
BANNED_WORDS = ("turbo", "repeat", "toggle", "chord", "delay", "hold_repeat")
# the only mouse-ish group modes a cursor may use: relative movement, never a jump to a point
ALLOWED_MOUSE_MODES = {"mouse_joystick", "trackball", "absolute_mouse"}
JUMP_MODES = {"mouse_region", "scrollwheel_jump", "touch_menu_jump"}


def layouts():
    for t in install_wheel.CONTROLLER_TYPES:
        yield t, install_wheel.build_layout(t)


def inputs(text):
    return re.findall(r'"activators"\n\t+\{(.*?)\n\t+\}\n\t+\}', text, re.S)


class CursorPolicy(unittest.TestCase):
    def test_every_input_has_one_plain_press_and_one_binding(self):
        for t, text in layouts():
            for m in re.finditer(r'\t\t\t"(\w+)"\n\t\t\t\{\n\t\t\t\t"activators"\n(.*?)\n\t\t\t\}\n', text, re.S):
                name, body = m.groups()
                acts = re.findall(r'"(\w+_Press|\w+_Press_\w+|Release|Chord\w*)"\n', body)
                self.assertEqual(acts, ["Full_Press"], f"{t} {name}")
                self.assertEqual(len(re.findall(r'"binding"', body)), 1, f"{t} {name}")
                self.assertFalse(re.search(r'binding"\t\t"[^"]*,[^"]*;', body), f"{t} {name}: chained")

    def test_no_banned_activator_or_setting_anywhere(self):
        for t, text in layouts():
            for a in BANNED_ACTIVATORS:
                self.assertNotIn(a, text, f"{t}: {a}")
            low = text.lower()
            for w in BANNED_WORDS:
                self.assertNotIn(f'"{w}', low, f"{t}: {w}")
                self.assertNotRegex(low, rf'"[a-z_]*{w}[a-z_]*"\t\t"1"', f"{t}: {w} on")

    def test_a_mouse_mode_is_relative_and_clicks_once(self):
        for t, text in layouts():
            for m in re.finditer(r'"mode"\t\t"(\w+)"', text):
                self.assertNotIn(m.group(1), JUMP_MODES, t)
            clicks = re.findall(r'mouse_button \w+', text)
            self.assertEqual(len(clicks), len(set(clicks)), f"{t}: one click binding per button")
            for b in re.findall(r'"binding"\t\t"([^"]*)"', text):
                if "mouse_button" in b:
                    self.assertEqual(len(re.findall(r"mouse_button", b)), 1, t)
            for mode in re.findall(r'"mode"\t\t"(mouse\w*|trackball|absolute_mouse)"', text):
                self.assertIn(mode, ALLOWED_MOUSE_MODES, t)

    def test_the_top_slice_still_sends_no_key(self):
        for t, text in layouts():
            self.assertNotRegex(text, r'"touch_menu_button_1"\n', t)


if __name__ == "__main__":
    unittest.main()
