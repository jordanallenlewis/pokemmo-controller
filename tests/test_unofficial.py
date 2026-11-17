"""The same plain line says PokeMMO Controller is not an official PokeMMO tool,
in the first thing the installers print and on the remap screen. The wording is
fixed: change it everywhere or nowhere."""
import unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
LINE = ("PokeMMO Controller is an unofficial, fan-made tool, made by and for PokeMMO players. "
        "It is not made, endorsed or supported by the PokeMMO team.")


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class Unofficial(unittest.TestCase):
    def test_installers_print_it_first(self):
        for name in ("install.sh", "install.ps1"):
            text = read(name)
            self.assertEqual(text.count(LINE), 1, name)
            self.assertLess(text.index(LINE), text.index("Downloading pokemmo-controller"), name)

    def test_remap_screen_says_it(self):
        self.assertIn(LINE, read("tools/ui_page.html"))

    def test_no_wording_that_suggests_approval(self):
        for name in ("install.sh", "install.ps1", "tools/ui_page.html"):
            low = read(name).lower()
            for bad in ("official partner", "officially supported", "approved by pokemmo", "in partnership"):
                self.assertNotIn(bad, low, name)


if __name__ == "__main__":
    unittest.main()
