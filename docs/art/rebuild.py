"""One command rebuilds every generated graphic from the canonical source (brand/tokens.json, tools/layout.py,
the photos and the site's logo files):

    python docs/art/rebuild.py            banners + social card (stdlib only), then, if node and Playwright
                                          are present, og.png and the controller maps / wheel
    python docs/art/rebuild.py --check    fail if anything generated is stale or not in docs/art/graphics.json

Changing a token (colour, font, size) or a term in brand/tokens.json, or a default in tools/layout.py,
regenerates every graphic. The graphics registry is docs/art/graphics.json.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ART = ROOT / "docs" / "art"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv):
    if "--check" in argv:
        sys.path.insert(0, str(ROOT / "tests"))
        import unittest
        return 0 if unittest.main(module="test_graphics", argv=["x"], exit=False).result.wasSuccessful() else 1
    load("art_build", ART / "build.py").main()
    node = shutil.which("node")
    if not node:
        print("node not found: skipped og.png and the maps (they need node + Playwright)")
        return 0
    subprocess.run([node, str(ART / "raster.js"), str(ROOT / "site/assets/og.svg"), str(ROOT / "site/assets/og.png")], check=True)
    sys.path.insert(0, str(ROOT / "site"))
    load("art_render", ART / "render.py").render()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
