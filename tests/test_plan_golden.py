"""helper/plan_test.go replays tests/golden/plan-parity.json. This keeps that file exactly
what the Python install Plan does today."""
import unittest

import helpers  # noqa: F401
import gen_plan_golden as G


class GoldenIsCurrent(unittest.TestCase):
    def test_file_matches_python(self):
        have = G.OUT.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(have, G.dump(), "run: python tests/gen_plan_golden.py --write")


if __name__ == "__main__":
    unittest.main()
