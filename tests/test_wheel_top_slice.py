"""The top slice of the wheel does nothing, so a stray release of the right stick straight up
fires no action. Each action is still on the wheel once and presses one key."""
import re, unittest
from pathlib import Path

import helpers  # noqa: F401  (puts tools/ on the path)
import layout as L
import install_wheel

PAGE = (Path(__file__).resolve().parent.parent / "tools" / "ui_page.html").read_text(encoding="utf-8")


def slices(text):
    return dict(re.findall(r'"touch_menu_button_(\d+)"\s*\{.*?"binding"\s*"key_press ([^,]+),', text, re.S))


class TopSlice(unittest.TestCase):
    def build(self, t="controller_xboxone"):
        return install_wheel.encode(install_wheel.build_layout(t)).decode("utf-8")

    def test_the_top_slice_has_no_binding(self):
        for t in install_wheel.CONTROLLER_TYPES:
            self.assertNotIn("touch_menu_button_1\"", self.build(t), t)

    def test_actions_follow_the_empty_top_slice_in_order(self):
        got = slices(self.build())
        want = {str(i): key for i, (key, _) in enumerate(L.wheel_slices(L.default_layout()), start=2)}
        self.assertEqual(got, want)

    def test_button_count_covers_centre_empty_slice_and_every_action(self):
        self.assertIn(f'"touch_menu_button_count"\t\t"{L.WHEEL_SIZE + 2}"', self.build())

    def test_each_action_is_once_and_one_key(self):
        keys = list(slices(self.build()).values())
        self.assertEqual(len(keys), L.WHEEL_SIZE)
        self.assertEqual(len(set(keys)), L.WHEEL_SIZE)

    def test_preview_in_the_remap_screen_shows_the_empty_top_slice(self):
        self.assertIn("Does nothing", PAGE)


if __name__ == "__main__":
    unittest.main()
