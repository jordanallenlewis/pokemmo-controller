"""The Go helper is checked against tests/golden/layout-parity.json. This test keeps that file
honest: it must be exactly what the Python layout core says today."""
import unittest

import helpers  # noqa: F401
import gen_layout_golden as G


class GoldenIsCurrent(unittest.TestCase):
    def test_file_matches_python(self):
        have = G.OUT.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(have, G.dump(), "run: python tests/gen_layout_golden.py --write")

    def test_policy_cases_are_refused(self):
        import json
        data = json.loads(G.dump())
        by = {c["label"]: c for c in data["cases"]}
        for label in ["turbo field", "repeat field", "macro field", "shared input", "button and axis",
                      "list spec", "wheel twice", "trigger released", "right stick", "duplicate bind"]:
            self.assertFalse(by[label]["ok"], label)
        for label in ["default", "swap buttons", "trigger moved", "unbound action"]:
            self.assertTrue(by[label]["ok"], label)


if __name__ == "__main__":
    unittest.main()
