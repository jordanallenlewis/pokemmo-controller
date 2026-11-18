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


if __name__ == "__main__":
    unittest.main()
