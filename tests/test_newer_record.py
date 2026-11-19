"""An install record written by a newer PokeMMO Controller (2.x, record_format 2 and up) is
never overwritten by this 1.x tool: install, update, dry run and every other writer refuse with
"Made by a newer PokeMMO Controller. Use pmc." and change nothing. Uninstall still works from the
record's files{} alone, so a player can always get back to how things were (docs/FOUNDATION.md M1).
"""
import json, unittest

from helpers import Sandbox  # noqa: F401  (sets the test flag before the tools load)
from test_setup import Base, diff
import test_pmc
import common

NEWER = "Made by a newer PokeMMO Controller. Use pmc."


def record_path(sb):
    return sb.pokemmo / "config" / common.STATE_NAME


def make_newer(sb, **fields):
    """Turn the record a 1.x install wrote into one a newer version wrote (same locked keys)."""
    p = record_path(sb)
    rec = json.loads(p.read_text(encoding="utf-8"))
    rec.update(fields)
    p.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class NewerRecord(Base):
    def installed_newer(self, **fields):
        sb = self.make()
        pristine = sb.snapshot()
        sb.setup()
        make_newer(sb, **fields)
        return sb, pristine

    def assertRefused(self, sb, *args):
        before = sb.snapshot()
        r = sb.setup(*args, check=False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(NEWER, r.stdout + r.stderr)
        self.assertIn("Nothing was changed", r.stdout + r.stderr)
        self.assertEqual(diff(before, sb.snapshot()), [], "a refused run changed files")
        return r

    def test_install_refuses_a_record_with_a_newer_format(self):
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        self.assertRefused(sb)

    def test_any_format_this_version_did_not_write_is_refused(self):
        for value in (3, 2, "2", 0, True, 1.5):
            with self.subTest(record_format=value):
                sb, _ = self.installed_newer(record_format=value)
                self.assertRefused(sb)

    def test_options_that_change_the_install_are_refused_too(self):
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        for args in (("--no-wheel",), ("--reset-layout",), ("--follow-at-login",), ("--switch-positional",)):
            with self.subTest(args=args):
                self.assertRefused(sb, *args)

    def test_dry_run_says_so_before_anything_else(self):
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        self.assertRefused(sb, "--dry-run")

    def test_uninstall_still_puts_everything_back_from_files_alone(self):
        sb, pristine = self.installed_newer(record_format=2, version="2.0.0", engine="rust")
        r = sb.setup("--uninstall")
        self.assertIn("Removed", r.stdout)
        self.assertEqual(diff(pristine, sb.snapshot()), [])

    def test_a_record_from_this_version_or_an_older_one_still_installs(self):
        # an older 1.x record is the normal update path; record_format 1 or absent is today's format
        for fields in ({"version": "1.0.0"}, {"record_format": 1}, {"record_format": None}):
            with self.subTest(fields=fields):
                sb, _ = self.installed_newer(**fields)
                r = sb.setup()
                self.assertNotIn(NEWER, r.stdout + r.stderr)
                rec = json.loads(record_path(sb).read_text(encoding="utf-8"))
                self.assertEqual(rec["version"], common.VERSION)

    def test_a_newer_version_in_todays_format_still_installs_so_an_update_can_roll_back(self):
        # the updater rolls back by running the previous copy over the record the newer copy wrote
        sb, _ = self.installed_newer(version="9.9.9")
        r = sb.setup()
        self.assertNotIn(NEWER, r.stdout + r.stderr)

    def test_every_writer_goes_through_the_same_refusal(self):
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        before = sb.snapshot()
        p = common.Plan(sb.pokemmo)
        p.put(sb.props, b"changed\n")
        with self.assertRaises(SystemExit) as e:
            p.commit()
        self.assertIn(NEWER, str(e.exception.code))
        with self.assertRaises(SystemExit):
            common.Plan(sb.pokemmo).save_state()
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_the_updater_neither_updates_nor_writes_its_settings(self):
        import updater
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        before = sb.snapshot()
        with self.assertRaises(updater.UpdateError) as e:
            updater.apply(sb.pokemmo, {"version": "1.9.0"}, say=lambda *_: None)
        self.assertIn(NEWER, str(e.exception))
        self.assertFalse(updater.save_settings(sb.pokemmo, channel="beta"))
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_the_helper_at_login_stops_by_itself(self):
        import setup
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        self.assertFalse(setup.follower_wanted(sb.pokemmo))

    def test_the_rule_itself(self):
        self.assertFalse(common.newer_record({}))
        self.assertFalse(common.newer_record({"record_format": None, "version": common.VERSION}))
        self.assertFalse(common.newer_record({"record_format": 1, "version": "1.3.0"}))
        self.assertFalse(common.newer_record({"version": "9.9.9"}))
        self.assertTrue(common.newer_record({"record_format": 2}))
        self.assertTrue(common.newer_record({"record_format": 3, "version": "2.0.0"}))


class NewerRecordThroughPmc(Base):
    pmc = test_pmc.PMC.pmc   # its helpers only, not its tests
    js = test_pmc.PMC.js

    def test_pmc_install_exits_6_with_the_stable_code(self):
        sb = self.make()
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        make_newer(sb, record_format=2, version="2.0.0")
        before = sb.snapshot()
        j = self.js(self.pmc(sb, "install", "--yes", "--no-follow", "--json", check=6))
        self.assertEqual(j["error"]["code"], "DATA_NEWER")
        self.assertIn(NEWER, j["error"]["message"])
        self.pmc(sb, "install", "--dry-run", "--no-follow", check=6)
        self.assertEqual(diff(before, sb.snapshot()), [])


if __name__ == "__main__":
    unittest.main()
