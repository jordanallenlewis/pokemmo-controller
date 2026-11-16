"""The README is the product surface: its links and pictures resolve, every
setup.py option is documented, and the first screen answers the three questions
a player has (does it work with my pad and system, how long, is it allowed)."""
import re, subprocess, sys, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


class Docs(unittest.TestCase):
    def test_local_links_and_images_exist(self):
        targets = re.findall(r'\]\(([^)#\s]+)', README) + re.findall(r'src="([^"]+)"', README)
        for t in targets:
            if t.startswith(("http://", "https://", "mailto:")):
                continue
            self.assertTrue((ROOT / t).exists(), f"README points at a missing file: {t}")

    def test_contents_anchors_exist(self):
        heads = {re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")
                 for h in re.findall(r"^#{2,3} (.+)$", README, re.M)}
        for a in re.findall(r"\]\(#([^)]+)\)", README):
            self.assertIn(a, heads, f"README contents links to a missing heading: #{a}")

    def test_every_setup_option_is_documented(self):
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "setup.py"), "--help"],
                             capture_output=True, text=True, check=True).stdout
        flags = set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", out)) - {"--help", "--version"}
        for f in sorted(flags):
            self.assertIn(f, README, f"README does not mention {f}")

    def test_first_screen_answers_pad_system_time_and_allowed(self):
        top = README.split("## Contents")[0].lower()
        for word in ("xbox", "playstation", "switch pro", "windows", "macos", "linux",
                     "steam deck", "one command", "allowed", "1 input = 1 action"):
            self.assertIn(word, top, f"the top of the README should say: {word}")

    def test_ui_has_a_screenshot_and_troubleshooting(self):
        self.assertIn("docs/remap-screen.png", README)
        self.assertRegex(README, r"(?m)^\*\*The remap screen")

    def test_claims_stay_honest(self):
        self.assertIn("not yet played on real hardware", README)

    def test_changelog_has_unreleased_and_is_plain(self):
        self.assertIn("## Unreleased", CHANGELOG)
        for bad in ("Trinity", "Claude", "agent"):
            self.assertNotIn(bad, CHANGELOG + README)


if __name__ == "__main__":
    unittest.main()
