"""The top slice of the wheel does nothing: letting go of the right stick while it points straight
up must press no key (Jordan's own ask, 2026-11-17). Every slice with an action still presses exactly one key."""
import re, unittest

from helpers import TOOLS  # noqa: F401
import install_wheel


class TopSlice(unittest.TestCase):
    def slices(self, text):
        return dict(re.findall(r'"touch_menu_button_(\d+)"\n\t\t\t\{.*?"binding"\t\t"([^"]*)"', text, re.S))

    def test_top_slice_has_no_binding_and_the_rest_one_key_each(self):
        for t in install_wheel.CONTROLLER_TYPES:
            text = install_wheel.build_layout(t)
            got = self.slices(text)
            self.assertNotIn("1", got, t)                                  # top: nothing
            self.assertEqual(sorted(got, key=int), [str(i) for i in range(2, 12)], t)
            for b in got.values():
                self.assertEqual(len(re.findall(r"key_press", b)), 1)      # one key per slice
            self.assertIn('"touch_menu_button_count"\t\t"12"', text)       # 11 slices + centre
            self.assertTrue(got["2"].startswith("key_press N, Pokedex"))

    def test_the_layouts_in_the_repo_match_what_the_installer_writes(self):
        for t in install_wheel.CONTROLLER_TYPES:
            f = install_wheel.OUT_DIR / f"{t}.vdf"
            self.assertEqual(f.read_bytes().replace(b"\r\n", b"\n"), install_wheel.build_layout(t).encode(), t)


if __name__ == "__main__":
    unittest.main()
