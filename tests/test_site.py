"""The site must show its content without waiting for any animation or script."""
import re
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


class VisibleByDefault(unittest.TestCase):
    def css(self):
        return (SITE / "styles.css").read_text(encoding="utf-8")

    def test_no_keyframe_starts_transparent(self):
        # A fade-in from opacity 0 leaves a half-drawn page on slow phones and in
        # a capture taken at load. Motion may move things; it never hides them.
        for body in re.findall(r"@keyframes\s+[\w-]+\s*\{(.*?)\}\s*\}", self.css(), re.S):
            self.assertNotRegex(body, r"opacity\s*:\s*0(?![.\d])", body)

    def test_nothing_is_hidden_until_a_script_runs(self):
        css = self.css()
        self.assertNotRegex(css, r"\.(reveal|js-hidden)[^{]*\{[^}]*opacity\s*:\s*0(?![.\d])")


class InstallChooser(unittest.TestCase):
    def html(self):
        return (SITE / "index.html").read_text(encoding="utf-8")

    def test_every_system_has_a_tab_and_a_panel(self):
        html = self.html()
        for os_id in ("win", "mac", "linux", "deck"):
            self.assertIn(f'data-os-tab="{os_id}"', html)
            self.assertIn(f'data-os-panel="{os_id}"', html)

    def test_the_hero_names_the_other_systems(self):
        self.assertIn("data-other-os", self.html())

    def test_phones_are_told_the_truth(self):
        js = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn("mobile", js)


if __name__ == "__main__":
    unittest.main()
