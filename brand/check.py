"""Canon check: one source for fonts, type sizes, images and words (brand/).

    python brand/check.py         exit 1 and list every drift

Checks, over everything a player or contributor can read:
  words   a term from brand/glossary.json "wrong_to_right" outside its allowed context
  fonts   a font-family that is not in brand/tokens.json fonts.allowed
  sizes   a font-size that is not on brand/tokens.json scale (px, rem, or the fluid values)
  images  an image in a README, doc or page that is not in the canonical set (brand/images.json)
brand/known-drift.json lists drift that exists today (sizes the site and app still use off the scale; burn it down); it can only shrink (the test fails if an
entry no longer matches anything, or if there is drift not listed). Standard library only.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "brand"
TEXT = ["README.md", "CONTRIBUTING.md", "CHANGELOG.md", "docs/*.md", "site/index.html", "site/404.html",
        ".github/**/*.md", ".github/ISSUE_TEMPLATE/*", "install.sh", "install.ps1", "tools/*.py", "tools/ui_page.html"]
STYLE = ["site/styles.css", "tools/ui_page.html", "docs/img/*.svg"]
IMG_DOCS = ["README.md", "CONTRIBUTING.md", "docs/*.md", ".github/**/*.md"]


def load(name):
    if name == "tokens.json":                       # W3C format on disk, flat shape for the checks
        import tokens
        return tokens.flat(B / name)
    return json.loads((B / name).read_text(encoding="utf-8"))


def files(globs):
    seen = []
    for g in globs:
        for p in sorted(ROOT.glob(g)):
            if p.is_file() and p not in seen:
                seen.append(p)
    return seen


def strip_blobs(text):
    return re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+", "data:", text)


def words():
    g, out = load("glossary.json"), []
    allowed = g["allowed_context"]
    for p in files(TEXT):
        for n, line in enumerate(strip_blobs(p.read_text(encoding="utf-8", errors="replace")).splitlines(), 1):
            scrub = re.sub(r"https?://\S+", lambda m: "\0" * len(m.group()), line)  # a link's address is not our wording
            for a in allowed:
                scrub = re.sub(re.escape(a), "\0" * len(a), scrub, flags=re.I)
            for w in g["wrong_to_right"]:
                flags = 0 if w.get("case_sensitive") else re.I
                if re.search(rf"(?<![\w-]){re.escape(w['wrong'])}(?![\w-])", scrub, flags):
                    out.append(f"{p.relative_to(ROOT).as_posix()}:{n}: '{w['wrong']}' should be '{w['right']}'")
    return out


def fonts_and_sizes():
    t, out = load("tokens.json"), []
    allowed = {f.lower() for f in t["fonts"]["allowed"]}
    px = {f"{v}px" for v in t["scale"]["px"].values()}
    rem = {f"{v:g}rem".replace("0.", ".", 1) if v < 1 else f"{v:g}rem" for v in t["scale"]["rem"].values()}
    fluid = {re.sub(r"\s+", "", f) for f in t["scale"]["fluid"]}
    for p in files(STYLE):
        text = strip_blobs(p.read_text(encoding="utf-8", errors="replace"))
        if p.suffix == ".html":                      # only the page's own style block, after the generated tokens
            m = re.search(r"/\*brand:end\*/(.*?)</style>", text, re.S)
            text = m.group(1) if m else ""
        for n, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"font-family\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^;}\"]*)", line):
                val = m.group(1).strip("\"'")
                if "var(" in val:
                    continue
                for fam in re.split(r"\s*,\s*", val):
                    fam = fam.strip().strip("\"'")
                    if fam and fam.lower() not in allowed:
                        out.append(f"{p.relative_to(ROOT).as_posix()}:{n}: font '{fam}' is not in brand/tokens.json fonts.allowed")
            for m in re.finditer(r"(?<![\w-])font\s*:\s*(?:(?:italic|normal|bold|\d{3})\s+)*([\d.]+(?:px|rem))(?:/[^\s;}]+)?\s+(?:var\(|[\"'a-zA-Z])", line):
                v = m.group(1).replace("0.", ".", 1) if m.group(1).startswith("0.") else m.group(1)
                if v not in px and v not in rem:
                    out.append(f"{p.relative_to(ROOT).as_posix()}:{n}: size '{m.group(1)}' (font shorthand) is not on the scale in brand/tokens.json")
            for m in re.finditer(r"font-size\s*[:=]\s*(?:\"|')?\s*([^;}\"']+)", line):
                val = re.sub(r"\s*!important", "", m.group(1).strip())
                v = re.sub(r"\s+", "", val)
                if "var(" in val or v in px or v in rem or v in fluid or v in ("inherit", "100%"):
                    continue
                if re.fullmatch(r"[\d.]+(px)?", v) and p.suffix == ".svg":
                    continue                          # SVG art is scaled as a picture
                out.append(f"{p.relative_to(ROOT).as_posix()}:{n}: size '{val}' is not on the scale in brand/tokens.json")
    return out


def images():
    canon, out = load("images.json"), []
    ok_files = {s for s in canon["files"]}
    ok_globs = canon["globs"]
    def allowed(ref):
        if ref.startswith(("http://", "https://")):
            return any(ref.startswith(h) for h in canon["external_ok"])
        rel = ref.split("#")[0].split("?")[0]
        return rel in ok_files or any(Path(rel).match(g) for g in ok_globs)
    for p in files(IMG_DOCS):
        text = strip_blobs(p.read_text(encoding="utf-8", errors="replace"))
        for n, line in enumerate(text.splitlines(), 1):
            refs = re.findall(r"<img[^>]*?\ssrc=\"([^\"]+)\"", line) + re.findall(r"!\[[^\]]*\]\(([^)\s]+)", line)
            for r in refs:
                if not allowed(r):
                    out.append(f"{p.relative_to(ROOT).as_posix()}:{n}: image '{r}' is not in the canonical set (brand/images.json)")
    return out


def run():
    found = [re.sub(r":\d+:", ":", f, count=1) for f in words() + fonts_and_sizes() + images()]  # no line numbers: edits shift them
    known = set(load("known-drift.json")["entries"])
    new = [f for f in found if f not in known]
    gone = sorted(known - set(found))
    return new, gone


if __name__ == "__main__":
    if "--list" in sys.argv:                          # print current drift in known-drift format
        print(json.dumps({"entries": sorted({re.sub(r":\d+:", ":", f, count=1) for f in words() + fonts_and_sizes() + images()})}, indent=1))
        sys.exit(0)
    new, gone = run()
    for x in new:
        print("DRIFT", x)
    for x in gone:
        print("FIXED, remove from brand/known-drift.json:", x)
    sys.exit(1 if new or gone else 0)
