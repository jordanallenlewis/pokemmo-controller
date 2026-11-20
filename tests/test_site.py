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


class Sections(unittest.TestCase):
    """How it works, what's new, roadmap and the help-test call are on the page."""

    def html(self):
        return (SITE / "index.html").read_text(encoding="utf-8")

    def test_every_section_has_an_anchor_and_a_nav_link_for_how(self):
        html = self.html()
        for sid in ("how", "install", "faq", "new", "roadmap", "help-test", "uninstall", "troubleshooting"):
            self.assertIn('id="%s"' % sid, html)
        self.assertIn('href="#how"', html)

    def test_roadmap_matches_the_readme(self):
        readme = (SITE.parent / "README.md").read_text(encoding="utf-8")
        road = readme.split("## Roadmap", 1)[1].split("## Tested with", 1)[0]
        for item in ("Cursor mode", "Steam Deck back-button variant", "Steam community layout"):
            self.assertIn(item.lower(), road.lower())
            self.assertIn(item.lower(), self.html().lower())

    def test_untested_systems_are_not_claimed(self):
        html = self.html()
        self.assertIn("have not been played in game yet", html)
        self.assertNotRegex(html, r"(?i)tested on (a )?(mac|deck|playstation|switch)")

    def test_whats_new_names_the_latest_unreleased_headline(self):
        log = (SITE.parent / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## Unreleased", log)
        self.assertIn("Update with one click", self.html())

    def test_faq_covers_the_friction_list(self):
        html = self.html()
        for q in ("paste a line", "PokeMMO be closed", "Steam close", "isn't detected"):
            self.assertIn(q.lower(), html.lower())


class FooterCredit(unittest.TestCase):
    def test_footer_credits_the_creator_with_a_real_link(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        foot = html[html.index('<footer class="foot">'):html.index("</footer>")]
        self.assertRegex(foot, r'Made by <a href="https://jordanallenlewis\.com/\?utm_source=pokemmocontroller[^"]*">Jordan Allen Lewis</a>')
        self.assertIn("unofficial, fan-made tool", foot)
        self.assertIn("Controller photo:", foot)


if __name__ == "__main__":
    unittest.main()
