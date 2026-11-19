"""One source for the look: brand/tokens.json (W3C Design Tokens format; brand/tokens.py reads it).

    python brand/build.py          write brand/tokens.css and put the same text into tools/ui_page.html
    python brand/build.py --check  fail if either is out of date (the tests run this)

The remap page carries its own copy (it must work with nothing else installed);
site/styles.css uses the same dark values (tests/test_brand.py compares them).
Standard library only.
"""
import base64, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokens as _tokens

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "brand" / "tokens.json"
PAGE = ROOT / "tools" / "ui_page.html"


def css(t=None):
    t = t or _tokens.flat(TOKENS)
    def block(name):
        return "".join(f"  --{k}: {v};\n" for k, v in t[name].items())
    fonts = "".join(f"  --{k}: {v};\n" for k, v in t["type"].items())
    return (f":root {{\n{block('dark')}{fonts}  --radius: {t['radius']};\n  color-scheme: dark;\n}}\n"
            f"@media (prefers-color-scheme: light) {{\n:root {{\n{block('light')}  color-scheme: light;\n}}\n}}\n")


def mark_uri():
    data = (ROOT / "brand" / "mark.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")


def inject(page):
    page = re.sub(r"(/\*brand:start\*/\n).*?(/\*brand:end\*/)", lambda m: m.group(1) + css() + m.group(2), page, flags=re.S)
    page = re.sub(r"(<!--brand:mark-->).*?(<!--/brand:mark-->)",
                  lambda m: f'{m.group(1)}<img class="mark" src="{mark_uri()}" alt="" width="32" height="32">{m.group(2)}', page, flags=re.S)
    return page


def main(argv):
    out = {ROOT / "brand" / "tokens.css": "/* Generated from tokens.json by build.py. Do not edit. */\n" + css(),
           PAGE: inject(PAGE.read_text(encoding="utf-8"))}
    stale = [str(p.relative_to(ROOT)) for p, text in out.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if "--check" in argv:
        if stale:
            print("out of date, run python brand/build.py:", ", ".join(stale))
            return 1
        return 0
    for p, text in out.items():
        p.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
