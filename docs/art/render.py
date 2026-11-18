"""Renders the README's controller maps and the wheel picture from the real photos.

    python docs/art/render.py          write docs/img/map-*.png, wheel-*.png and docs/img/maps.json
    python docs/art/render.py --check  fail if those pictures no longer match their inputs (the tests run this)

Nothing is drawn here. The pictures are screenshots of the website's own button map and wheel
(site/index.html + site/app.js), which show the photos in site/assets/ and docs/xbox-controller.webp
with the hotspots in site/data/hotspots.json and the names and actions from tools/layout.py, through
site/data/layout.json. Each is at least 3840 pixels wide, in a light and a dark variant.

Writing them needs Node and Playwright (a developer tool; the player's install needs neither).
Checking needs only Python: docs/img/maps.json records a hash of everything the pictures are made from,
so changing the layout, a name, a hotspot, a photo or the tokens without re-rendering fails the check
(a website change that does not touch the map is not a reason to re-render).

    NODE_PATH=<folder with playwright> PLAYWRIGHT_BROWSERS_PATH=<browsers> python docs/art/render.py
"""
import functools
import hashlib
import http.server
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "brand"))
import tokens as brand_tokens  # noqa: E402
IMG = ROOT / "docs" / "img"
MANIFEST = IMG / "maps.json"
MIN_WIDTH = 3840
KINDS = ("xbox", "playstation", "switch", "deck")
THEMES = ("light", "dark")
NAMES = [f"map-{k}-{t}.png" for k in KINDS for t in THEMES] + [f"wheel-{t}.png" for t in THEMES]


def inputs():
    """Everything the pictures are made from."""
    hot = json.loads((ROOT / "site" / "data" / "hotspots.json").read_text(encoding="utf-8"))["pads"]
    # Not the page itself (index.html, styles.css, app.js): other changes to the website must not fail this check.
    files = ["site/data/layout.json", "site/data/hotspots.json", "brand/tokens.json", "docs/art/shot.js"] \
        + sorted({hot[k]["photo"] for k in hot})
    return files


def fingerprint():
    h = hashlib.sha256()
    for f in inputs():
        data = (ROOT / f).read_bytes()
        if not f.endswith(".webp"):                 # text files: a Windows checkout may turn LF into CRLF
            data = data.replace(b"\r\n", b"\n")
        h.update(f.encode() + b"\0" + data + b"\0")
    return h.hexdigest()


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


def check():
    problems = []
    if not MANIFEST.exists():
        return [f"{MANIFEST.relative_to(ROOT)} is missing: run python docs/art/render.py"]
    rec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if rec.get("inputs") != fingerprint():
        problems.append("the layout, names, hotspots, photos or the site page changed since the pictures were "
                        "rendered: run python docs/art/render.py and commit docs/img")
    for n in NAMES:
        p = IMG / n
        if not p.exists():
            problems.append(f"{n} is missing")
        elif png_size(p)[0] < MIN_WIDTH:
            problems.append(f"{n} is {png_size(p)[0]} pixels wide, under {MIN_WIDTH}")
    extra = sorted(p.name for p in IMG.glob("*.png") if p.name not in NAMES)
    if extra:
        problems.append("unexpected pictures in docs/img: " + ", ".join(extra))
    return problems


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def translate_path(self, path):
        alias = {"/assets/controller.webp": "docs/xbox-controller.webp"}
        p = path.split("?")[0]
        if p in alias:
            return str(ROOT / alias[p])
        return super().translate_path(path)


def render():
    sys.path.insert(0, str(ROOT / "site"))
    import build  # noqa: E402  (writes nothing here; just makes sure layout.json is current)
    if any(build.outputs()[p] != Path(p).read_text(encoding="utf-8").replace("\r\n", "\n") for p in build.outputs()):
        sys.exit("generated copies are stale: run python site/build.py first")
    handler = functools.partial(Quiet, directory=str(ROOT / "site"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    IMG.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:       # shot.js reads the flat shape of the tokens
            flat = Path(tmp) / "tokens-flat.json"
            flat.write_text(json.dumps(brand_tokens.flat()), encoding="utf-8")
            subprocess.run(["node", str(ROOT / "docs" / "art" / "shot.js"), url, str(IMG), str(flat)], check=True)
    finally:
        srv.shutdown()
    sizes = {n: list(png_size(IMG / n)) for n in NAMES}
    for n, (w, h) in sizes.items():
        if w < MIN_WIDTH:
            sys.exit(f"{n} came out {w} pixels wide")
    MANIFEST.write_text(json.dumps({"inputs": fingerprint(), "pictures": sizes}, indent=1) + "\n", encoding="utf-8")
    print("wrote", len(NAMES), "pictures to docs/img")


def main(argv):
    if argv[:1] == ["--check"]:
        probs = check()
        for p in probs:
            print(p, file=sys.stderr)
        return 1 if probs else 0
    render()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
