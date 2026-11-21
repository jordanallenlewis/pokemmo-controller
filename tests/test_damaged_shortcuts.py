"""A Steam shortcuts.vdf that is damaged must give the "Could not read" note, never a crash.

A crash or power loss can leave a file full of zero bytes. Read as binary VDF, every two zero bytes
open one more nested section, so a file of a few kilobytes used to run Python out of recursion and
stop the install (and uninstall) with a traceback. The reader now refuses nesting deeper than 64
sections, the same limit the helper's reader uses (helper/shortcuts.go bvMaxDepth); Steam itself
writes three levels.

Two more inputs Steam never writes used to crash instead of being handled: a section key made of
non-ASCII digits (str.isdigit is true for "²", int() is not) and a 64-bit or float appid (kept as
raw bytes, which could not go into a set).
"""
import struct
import unittest

from helpers import GAME, Sandbox, shortcuts
import install_wheel as W

USER = "userdata/12345/config/shortcuts.vdf"
ZEROS = b"\0" * 4096


def chain(levels):
    """Top section holding `levels` sections nested one in another (top counts as level 0)."""
    head = b"".join(b"\0" + f"k{n}".encode() + b"\0" for n in range(levels))
    return head + b"\x08" * (levels + 1)


class DamagedFile(unittest.TestCase):
    def test_install_with_a_zero_filled_file_notes_it_and_leaves_it(self):
        sb = Sandbox()
        self.addCleanup(sb.cleanup)
        f = sb.steam / USER
        f.write_bytes(ZEROS)
        r = sb.setup()
        out = r.stdout + r.stderr
        self.assertNotIn("Traceback", out)
        self.assertIn("Could not read", out)
        self.assertEqual(f.read_bytes(), ZEROS)

    def test_uninstall_with_a_file_damaged_after_install_notes_it(self):
        sb = Sandbox()
        self.addCleanup(sb.cleanup)
        f = sb.steam / USER
        f.write_bytes(shortcuts({"0": dict(GAME)}))
        sb.setup()
        f.write_bytes(ZEROS)
        r = sb.setup("--uninstall")
        out = r.stdout + r.stderr
        self.assertNotIn("Traceback", out)
        self.assertIn("Could not read", out)
        self.assertEqual(f.read_bytes(), ZEROS)


class Reader(unittest.TestCase):
    def test_zero_bytes_are_unreadable_not_a_crash(self):
        with self.assertRaises(ValueError):
            W.read_shortcuts(ZEROS)

    def test_nesting_limit_matches_the_helper(self):
        ok = chain(64)
        top, end = W.parse_bvdf(ok)
        self.assertEqual(end, len(ok))
        with self.assertRaises(ValueError):
            W.parse_bvdf(chain(65))

    def test_non_ascii_digit_key(self):
        sc = {"0": dict(GAME), "²": dict(GAME, AppName="Other")}
        self.assertEqual(W.next_key(sc), "1")
        old = {"²": dict(GAME, AppName="Lost", Exe='"/lost"')}
        self.assertEqual(W.restore_lost_shortcuts(sc, old), ["Lost"])

    def test_raw_appid_on_restore(self):
        raw = W.Raw(7, struct.pack("<q", 1 << 40))
        sc = {"0": dict(GAME, appid=raw)}
        old = {"0": dict(GAME, appid=W.Raw(7, struct.pack("<q", 1 << 40))),
               "1": dict(GAME, appid=W.Raw(7, struct.pack("<q", 7)), AppName="Lost")}
        self.assertEqual(W.restore_lost_shortcuts(sc, old), ["Lost"])


if __name__ == "__main__":
    unittest.main()
