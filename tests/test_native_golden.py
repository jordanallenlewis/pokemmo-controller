"""helper/nativemap_test.go replays tests/golden/native-parity.json. This keeps that file exactly
what the Python apply_native tool says today."""
import unittest

import helpers  # noqa: F401
import gen_native_golden as G


class GoldenIsCurrent(unittest.TestCase):
    def test_file_matches_python(self):
        have = G.OUT.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(have, G.dump(), "run: python tests/gen_native_golden.py --write")


if __name__ == "__main__":
    unittest.main()
