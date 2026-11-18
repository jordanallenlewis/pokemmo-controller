"""Graphics follow the canonical source. Every image is in docs/art/graphics.json with a class; every generated
SVG uses only the brand fonts (embedded, because GitHub cannot load web fonts for an image), only sizes and
weights from brand/tokens.json, and none of the spellings the glossary rules out; the social card is
what docs/art/build.py writes today. Standard library only."""
import base64, fnmatch, json, re, sys, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brand"))
import tokens as _t
TOK = _t.flat()
REG = json.loads((ROOT / "docs" / "art" / "graphics.json").read_text(encoding="utf-8"))["classes"]
EXT = {".png", ".svg", ".webp", ".jpg", ".jpeg", ".gif", ".mp4", ".webm"}
FIND = ("docs", "site/assets", "brand")


def images():
    for top in FIND:
        for p in (ROOT / top).rglob("*"):
            if p.is_file() and p.suffix.lower() in EXT:
                yield p.relative_to(ROOT).as_posix()


def generated_svgs():
    return [ROOT / f for f in images() if f.endswith(".svg") and any(fnmatch.fnmatch(f, g) for g in REG["generated"]["files"])]


class Registry(unittest.TestCase):
    def test_every_image_is_in_the_registry_once(self):
        for f in images():
            hits = [k for k, v in REG.items() if any(fnmatch.fnmatch(f, g) for g in v["files"])]
            self.assertEqual(len(hits), 1, f"{f}: add it to docs/art/graphics.json under one class (found {hits})")

    def test_registry_names_no_missing_file(self):
        for k, v in REG.items():
            for g in v["files"]:
                self.assertTrue(any(fnmatch.fnmatch(f, g) for f in images()), f"{k}: {g} matches nothing")

    def test_every_generated_image_has_its_source(self):
        have = set(images())
        for f in have:
            if f.startswith("docs/img/") and f.endswith(".png"):
                continue        # maps and wheel: made by render.py, checked against their inputs in test_art
            if f.startswith("docs/img/") and f.endswith(".svg"):
                self.assertIn(f"docs/img/{Path(f).name}", have)
        self.assertTrue((ROOT / "docs/art/build.py").exists() and (ROOT / "docs/art/rebuild.py").exists())
        og_svg, og_png = ROOT / "site/assets/og.svg", ROOT / "site/assets/og.png"
        self.assertTrue(og_svg.exists() and og_png.exists(), "og.png needs its template og.svg")
        w = int.from_bytes(og_png.read_bytes()[16:20], "big")
        self.assertGreaterEqual(w, 2400)


class Svgs(unittest.TestCase):
    def test_fonts_are_the_canonical_ones_and_embedded(self):
        canon = {f["family"] for f in TOK["art"]["faces"].values()}
        for p in generated_svgs():
            t = p.read_text(encoding="utf-8")
            used = set(re.findall(r'font-family:"([^"]+)"', t))
            self.assertTrue(used <= canon and used, (p.name, used))
            self.assertNotIn("font-family=", re.sub(r"<style>.*?</style>", "", t, flags=re.S), p.name)
            data = {m.group(1) for m in re.finditer(r"src:url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)", t)}
            want = set()
            for k in ("display", "text", "mono"):
                f = TOK["art"]["faces"][k]
                if self._uses(t, k):
                    want.add(base64.b64encode((ROOT / f["file"]).read_bytes()).decode())
            self.assertEqual(data, want, f"{p.name}: embedded font files differ from the ones it uses")

    @staticmethod
    def _uses(t, kind):
        body = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
        if kind == "display":
            return 'class="d"' in body
        if kind == "mono":
            return 'class="m"' in body
        return bool(re.search(r'<text (?!class="[dm]")', body))

    def test_sizes_and_weights_come_from_the_scale(self):
        sizes, weights = set(TOK["art"]["sizes"]), {w for v in TOK["art"]["weights"].values() for w in v}
        for p in generated_svgs():
            t = re.sub(r"<style>.*?</style>", "", p.read_text(encoding="utf-8"), flags=re.S)
            for s in re.findall(r'<text [^>]*font-size="([\d.]+)"', t):
                self.assertIn(round(float(s)), sizes, f"{p.name}: font-size {s} is not in brand scale")
            for w in re.findall(r'font-weight="(\d+)"', t):
                self.assertIn(int(w), weights, f"{p.name}: weight {w} is not canonical")

    def test_heavy_text_is_display_and_light_text_is_text_face(self):
        for p in generated_svgs():
            t = p.read_text(encoding="utf-8")
            for tag in re.findall(r"<text [^>]*>", t):
                w = re.search(r'font-weight="(\d+)"', tag)
                heavy = bool(w and int(w.group(1)) >= 700)
                self.assertEqual('class="d"' in tag, heavy, (p.name, tag[:80]))

    def test_terms_follow_the_glossary(self):
        import check
        bad_words = [w for w, _, _ in check.forbidden(check.load("glossary.json"))]
        for p in generated_svgs():
            text = " ".join(re.findall(r">([^<>]+)<", re.sub(r"<style>.*?</style>", "", p.read_text(encoding="utf-8"), flags=re.S)))
            for bad in bad_words:
                self.assertNotRegex(text, r"\b" + re.escape(bad) + r"\b", f"{p.name}: use the canonical spelling, not '{bad}'")

    def test_social_card_uses_the_glossary(self):
        t = (ROOT / "site/assets/og.svg").read_text(encoding="utf-8")
        for w in (TOK["art"]["copy"]["domain"], *TOK["art"]["copy"]["platforms"][:3], TOK["art"]["copy"]["tagline"][1]):
            self.assertIn(w, t)

    def test_a_token_change_changes_the_graphics(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("b", ROOT / "docs/art/build.py")
        b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        before = b.og()
        b.TOKENS["art"]["copy"]["domain"] = "example.test"
        self.assertNotEqual(b.og(), before)

    def test_social_card_is_what_the_script_writes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("b2", ROOT / "docs/art/build.py")
        b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        self.assertEqual(b.og(), (ROOT / "site/assets/og.svg").read_text(encoding="utf-8").replace("\r\n", "\n"))


if __name__ == "__main__":
    unittest.main()
