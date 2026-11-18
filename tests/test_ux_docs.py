"""The friction list and the first-run journey stay honest and connected: every
ranked item says where it came from, and every local link resolves."""
import re, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
UX = ROOT / "docs" / "ux"


def items(text):
    """The numbered items of the ranked list, as separate blocks of text."""
    body = text.split("## The list", 1)[1].split("\n## ", 1)[0]
    return [m.strip() for m in re.split(r"\n(?=\d+\. )", "\n" + body) if re.match(r"\d+\. ", m.strip())]


class UxDocs(unittest.TestCase):
    def test_both_files_exist(self):
        for name in ("feedback.md", "journey.md"):
            self.assertTrue((UX / name).is_file(), f"docs/ux/{name} is missing")

    def test_every_friction_item_names_its_source(self):
        found = items((UX / "feedback.md").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(found), 5, "the ranked list should have items")
        for n, item in enumerate(found, 1):
            self.assertTrue(item.startswith(f"{n}. "), f"item {n} is out of order")
            self.assertRegex(item, r"Source: (Player|Measured|Review)",
                             f"item {n} does not say where it came from")

    def test_local_links_resolve(self):
        for path in UX.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)\s]+)\)", text):
                if target.startswith(("http://", "https://", "#")):
                    continue
                file = target.split("#", 1)[0]
                self.assertTrue((path.parent / file).resolve().exists(),
                                f"{path.name} links to a missing file: {target}")
                if "#" in target and file.endswith(".md"):
                    anchor = target.split("#", 1)[1]
                    heads = {re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")
                             for h in re.findall(r"^#{1,4} (.+)$", (path.parent / file).resolve()
                                                 .read_text(encoding="utf-8"), re.M)}
                    self.assertIn(anchor, heads, f"{path.name} links to a missing heading: {target}")


if __name__ == "__main__":
    unittest.main()
