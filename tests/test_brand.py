"""The look has one source (brand/tokens.json). The remap page carries a generated copy and the
site uses the same dark values; these tests fail when they drift apart."""
import json, re, subprocess, sys, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))
SITE_CSS = (ROOT / "site" / "styles.css").read_text(encoding="utf-8")
PAGE = (ROOT / "tools" / "ui_page.html").read_text(encoding="utf-8")


def luminance(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Brand(unittest.TestCase):
    def test_generated_files_are_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "brand" / "build.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_site_dark_values_match_the_tokens(self):
        d = TOKENS["dark"]
        for site, token in (("bg", "bg"), ("bg-2", "bg2"), ("surface", "surface"), ("surface-2", "surface2"),
                            ("ink", "ink"), ("muted", "muted"), ("dim", "dim"), ("yellow", "accent"),
                            ("yellow-ink", "accent-ink")):
            m = re.search(rf"--{re.escape(site)}:\s*(#[0-9a-fA-F]{{6}})", SITE_CSS)
            self.assertIsNotNone(m, site)
            self.assertEqual(m.group(1).lower(), d[token].lower(), f"site --{site} drifted from brand token {token}")

    def test_site_line_and_soft_accent_match_the_tokens(self):
        d = TOKENS["dark"]
        for site, token in (("line", "line"), ("accent-soft", "accent-soft")):
            m = re.search(rf"--{re.escape(site)}:\s*(rgba\([^)]*\))", SITE_CSS)
            self.assertIsNotNone(m, site)
            norm = lambda v: re.sub(r"\s+|(?<=[ ,.])0(?=\.)", "", v).replace("(0.", "(.")
            self.assertEqual(norm(m.group(1)), norm(d[token]), f"site --{site} drifted from brand token {token}")

    def test_text_is_readable_in_both_themes(self):
        for theme in ("dark", "light"):
            t = TOKENS[theme]
            for fg, bg in (("ink", "bg"), ("ink", "surface"), ("muted", "surface"), ("accent-ink", "accent"),
                           ("accent-text", "bg"), ("ok", "bg"), ("bad", "bg")):
                if t[fg].startswith("#") and t[bg].startswith("#"):
                    self.assertGreaterEqual(contrast(t[fg], t[bg]), 4.5, f"{theme}: {fg} on {bg}")
            self.assertGreaterEqual(contrast(t["dim"], t["surface"]) if t["dim"].startswith("#") else 4.5, 3.0, theme)

    def test_the_page_uses_the_tokens_not_its_own_colours(self):
        css = PAGE.split("/*brand:end*/")[1].split("</style>")[0]
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b", "a colour written into the page instead of a token")

    def test_the_mark_and_voice_files_exist(self):
        for name in ("mark.svg", "VOICE.md", "DESIGN.md", "tokens.css"):
            self.assertTrue((ROOT / "brand" / name).exists(), name)
        self.assertIn("unofficial, fan-made tool", (ROOT / "brand" / "VOICE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
