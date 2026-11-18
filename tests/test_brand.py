"""The look has one source (brand/tokens.json). The remap page carries a generated copy and the
site uses the same dark values; these tests fail when they drift apart."""
import json, re, subprocess, sys, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brand"))
import tokens as brand_tokens  # noqa: E402
TOKENS = brand_tokens.flat()
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

    def test_the_accent_is_the_pokemmo_logo_yellow_and_its_shades_follow(self):
        for theme in ("dark", "light"):
            self.assertEqual(TOKENS[theme]["accent"], "#f0ea6b")
        self.assertEqual(TOKENS["dark"]["accent-hover"], "#f5f199")
        self.assertGreaterEqual(contrast("#f0ea6b", TOKENS["dark"]["bg"]), 14.0)
        self.assertGreaterEqual(contrast(TOKENS["light"]["accent-text"], TOKENS["light"]["surface"]), 4.5)
        for site, token in (("yellow-hover", "accent-hover"), ("yellow-edge", "accent-edge")):
            m = re.search(rf"--{site}:\s*(#[0-9a-fA-F]{{6}})", SITE_CSS)
            self.assertEqual(m.group(1).lower(), TOKENS["dark"][token], site)

    def test_the_old_amber_is_gone_everywhere(self):
        old = re.compile(r"ffc833|ffd35c|c98a00|b07a00|7a5200|255,\s*200,\s*51", re.I)
        skip = {".git", "fonts"}
        for p in ROOT.rglob("*"):
            if not p.is_file() or skip & set(p.parts) or p.suffix.lower() not in (".css", ".html", ".svg", ".json", ".js", ".py", ".md"):
                continue
            if p.name == "test_brand.py":
                continue
            self.assertIsNone(old.search(p.read_text(encoding="utf-8", errors="ignore")), f"old amber in {p.relative_to(ROOT)}")

    def test_the_mark_and_voice_files_exist(self):
        for name in ("mark.svg", "VOICE.md", "DESIGN.md", "tokens.css"):
            self.assertTrue((ROOT / "brand" / name).exists(), name)
        self.assertIn("unofficial, fan-made tool", (ROOT / "brand" / "VOICE.md").read_text(encoding="utf-8"))


class DesignTokensFormat(unittest.TestCase):
    """brand/tokens.json is W3C Design Tokens (2025.10); the flat view must equal what it held before."""

    def setUp(self):
        self.raw = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))

    def test_flat_view_equals_the_values_from_before_the_conversion(self):
        before = json.loads((ROOT / "tests" / "golden" / "tokens-flat.json").read_text(encoding="utf-8"))
        self.assertEqual(brand_tokens.flat(), before)

    def test_every_token_has_a_type_and_a_value(self):
        def walk(node, kind, path):
            for k, v in node.items():
                if k.startswith("$") or not isinstance(v, dict):
                    continue
                here = v.get("$type", kind)
                if "$value" in v:
                    is_ref = isinstance(v["$value"], str) and v["$value"].startswith("{")   # a reference takes the type of its target
                    self.assertTrue(here or is_ref, f"{path}.{k} has no $type")
                else:
                    walk(v, here, f"{path}.{k}")
        walk(self.raw, None, "")

    def test_primary_is_the_accent_in_both_modes(self):
        self.assertEqual(self.raw["color"]["primary"]["$value"]["hex"], "#f0ea6b")
        for mode in ("dark", "light"):
            self.assertEqual(self.raw["color"][mode]["accent"]["$value"], "{color.primary}")
            self.assertEqual(TOKENS[mode]["accent"], "#f0ea6b")


if __name__ == "__main__":
    unittest.main()
