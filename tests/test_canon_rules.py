"""The canon check (brand/check.py): words, fonts, type sizes and images come from brand/.
A failure here names the file and line. Fix the text, or, for a real new term/size/image, add it to the source in brand/."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brand"))
import check  # noqa: E402


class CanonRules(unittest.TestCase):
    def test_no_new_drift_and_no_stale_exceptions(self):
        new, gone = check.run()
        self.assertEqual(new, [], "non-canonical word, font, size or image:\n" + "\n".join(new))
        self.assertEqual(gone, [], "fixed; remove from brand/known-drift.json:\n" + "\n".join(gone))

    def test_check_runs_from_the_command_line(self):
        r = subprocess.run([sys.executable, str(ROOT / "brand" / "check.py")], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_check_catches_each_kind_of_drift(self):
        g = check.load("glossary.json")
        self.assertTrue(any(w["wrong"] == "PokeMMO Controller Layout" for w in g["wrong_to_right"]))
        def scan(name, text):
            d = Path(tempfile.mkdtemp())
            (d / name).write_text(text, encoding="utf-8")
            old = (check.ROOT, check.TEXT, check.STYLE, check.IMG_DOCS)
            check.ROOT, check.TEXT, check.STYLE, check.IMG_DOCS = d, [name], [name], [name]
            try:
                return check.words(), check.fonts_and_sizes(), check.images()
            finally:
                check.ROOT, check.TEXT, check.STYLE, check.IMG_DOCS = old
        w, _, _ = scan("a.md", "Use the Playstation pad on Pokemmo with MacOS.")
        self.assertEqual(len(w), 3)
        _, f, _ = scan("a.css", "p { font-family: Comic Sans MS, sans-serif; font-size: 23px; }")
        self.assertEqual(len(f), 2)
        _, _, i = scan("a.md", '<img src="https://example.com/x.png"> ![x](docs/random.gif)')
        self.assertEqual(len(i), 2)

    def test_pad_family_names_are_what_the_layout_calls_them(self):
        import layout as L
        g = check.load("glossary.json")
        self.assertEqual(g["pad_families"], {k: v["title"] for k, v in L.PADS.items()})

    def test_canonical_images_exist(self):
        c = check.load("images.json")
        for f in c["files"]:
            self.assertTrue((ROOT / f).exists(), f)


if __name__ == "__main__":
    unittest.main()
