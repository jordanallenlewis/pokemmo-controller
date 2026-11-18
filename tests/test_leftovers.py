"""A process stopped while it waits for a busy file (Windows cannot let it clean up) leaves a
name.XXXX.tmp next to it. The next write and uninstall tidy those up."""
import os, time, unittest

from test_setup import Base, diff
import common


class Leftovers(Base):
    def test_uninstall_removes_leftovers_next_to_files_it_removes(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        layouts = sorted((sb.cfg / "pokemmo").glob("controller_*.vdf"))
        self.assertTrue(layouts)
        stray = layouts[0].with_name(layouts[0].name + ".abc123.tmp")
        stray.write_bytes(b"half a file")
        sb.setup("--uninstall")
        self.assertFalse(stray.exists())
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_uninstall_also_removes_a_leftover_of_the_state_file(self):
        # a wheel follower stopped mid-write leaves one next to the state file
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        state = sb.pokemmo / "config" / "pokemmo-controller.json"
        self.assertTrue(state.exists())
        stray = state.with_name(state.name + ".zskwxr2z.tmp")
        stray.write_bytes(b"half a file")
        sb.setup("--uninstall")
        self.assertFalse(stray.exists())
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_write_clears_old_leftovers_but_not_a_fresh_one(self):
        sb = self.make()
        target = sb.root / "x" / "file.txt"
        target.parent.mkdir()
        old = target.with_name("file.txt.old1.tmp")
        fresh = target.with_name("file.txt.new2.tmp")
        other = target.with_name("other.txt.zzz.tmp")
        for f in (old, fresh, other):
            f.write_bytes(b"x")
        t = time.time() - 600
        os.utime(old, (t, t))
        common.write_atomic(target, b"data")
        self.assertFalse(old.exists())      # stale: a killed run's
        self.assertTrue(fresh.exists())     # maybe another run is writing it right now
        self.assertTrue(other.exists())     # someone else's file
        self.assertEqual(target.read_bytes(), b"data")


if __name__ == "__main__":
    unittest.main()
