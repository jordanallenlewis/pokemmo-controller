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


class InstallFacts(unittest.TestCase):
    """The install section says what the installer does and how to undo it."""

    def html(self):
        return (SITE / "index.html").read_text(encoding="utf-8")

    def test_says_what_it_does_and_how_to_undo(self):
        html = self.html()
        self.assertIn("What this does to your computer", html)
        self.assertIn("How to undo it", html)
        self.assertIn("no administrator rights", html)

    def test_an_uninstall_line_for_every_kind_of_system(self):
        html = self.html()
        self.assertRegex(html, r'data-undo-panel="win"[\s\S]*?-Uninstall')
        self.assertRegex(html, r'data-undo-panel="unix"[\s\S]*?--uninstall')

    def test_the_uninstall_lines_match_the_readme(self):
        readme = (SITE.parent / "README.md").read_text(encoding="utf-8")
        for line in ("install.ps1))) -Uninstall", "install.sh | sh -s -- --uninstall"):
            self.assertIn(line, readme)
            self.assertIn(line.replace("&", "&amp;"), self.html())


if __name__ == "__main__":
    unittest.main()
