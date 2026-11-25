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

    def test_unofficial_line_under_the_hero_and_in_is_this_allowed(self):
        line = ("PokeMMO Controller is an unofficial, fan-made tool, made by and for PokeMMO players. "
                "It is not made, endorsed or supported by the PokeMMO team.")
        head, _, rest = README.partition("</h1>")
        self.assertIn(line, rest.split("Play [PokeMMO]")[0], "the line sits right under the hero")
        section = README.split("## Is this allowed?\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn(line, section)


    def test_ui_has_a_screenshot_and_troubleshooting(self):
        self.assertIn("docs/remap-screen.png", README)
        self.assertRegex(README, r"(?m)^<summary><b>The remap screen")

    def test_pad_side_profiles_and_turbo_are_named(self):
        # A pad's own app or turbo button works below this layout: the README must say so.
        head = "<summary><b>Controller not detected / buttons do nothing</b></summary>"
        self.assertIn(head, README)
        dead = README.split(head, 1)[1].split("</details>", 1)[0]
        self.assertRegex(dead, r"default profile", "buttons-do-nothing names pad-side app profiles")
        self.assertIn("## Is this allowed?\n", README)
        allowed = README.split("## Is this allowed?\n", 1)[1].split("\n## ", 1)[0]
        self.assertRegex(allowed, r"(?i)turbo button", "is-this-allowed says to keep pad turbo off")
        self.assertRegex(allowed, r"(?i)turbo and macros off")

    def test_lost_focus_has_a_troubleshooting_entry(self):
        # Most reported problem so far (#125, #126): a window that lost focus or a
        # button the stick cannot reach. The entry says what to try with the pad,
        # what still needs a mouse, and stays honest about what nobody has tested.
        head = "<summary><b>A window lost focus, or the stick cannot reach a button</b></summary>"
        self.assertIn(head, README)
        entry = README.split(head, 1)[1].split("</details>", 1)[0]
        self.assertIn("Focus Ring", entry)
        self.assertIn("(#roadmap)", entry, "points at cursor mode on the Roadmap")
        self.assertRegex(entry, r"(?i)mouse", "says what still needs a mouse")
        self.assertRegex(entry, r"(?i)not\s+(yet\s+)?(confirmed|played|tested)\s+on\s+real\s+hardware")
        how = README.split("## How do I… with a controller\n", 1)[1].split("\n## ", 1)[0]
        self.assertRegex(how, r"(?m)^\| Get back into a window .*\[Troubleshooting\]\(#troubleshooting\)")

    def test_claims_stay_honest(self):
        self.assertIn("not yet played on real hardware", README)

    def test_tested_with_names_every_ci_leg(self):
        """'Tested with' names every system the test workflow runs on, and keeps the Deck
        unverified, so the section cannot fall behind the CI matrix."""
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        jobs = workflow.split("\n  helper:", 1)[0]          # the sandbox test legs, not the helper app
        legs = (re.findall(r'label:\s*["\']([^"\']+)["\']', jobs)
                + re.findall(r'^    name:\s*["\']([^"\'$]+)["\']', jobs, re.M))
        self.assertGreaterEqual(len(legs), 10, legs)
        section = README.split("## Tested with\n", 1)[1].split("\n---", 1)[0]
        flat = " ".join(section.split())                    # the README is hard-wrapped
        oldest = re.search(r"oldest supported Python, 3\.9, on ([^(]+)\(", flat)
        self.assertTrue(oldest, "'Tested with' should say which systems also run Python 3.9")
        for leg in legs:
            system, _, python = leg.partition(", Python ")
            self.assertIn(system, flat, f"'Tested with' does not name the CI leg {leg!r}")
            if python == "3.9":
                self.assertIn(system, oldest.group(1), f"'Tested with' does not say {system} runs Python 3.9")
            elif python:
                self.assertIn(f"Python {python} on every system", flat)
        self.assertRegex(flat, r"Steam Deck: not yet played in game on a Deck")
        self.assertIn("Game Mode", flat)

    def test_changelog_has_unreleased_and_is_plain(self):
        self.assertIn("## Unreleased", CHANGELOG)
        for bad in ("Trinity", "Claude", "agent"):
            self.assertNotIn(bad, CHANGELOG + README)


if __name__ == "__main__":
    unittest.main()
