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
        sb = self.make()
        sb.setup("--follow-at-login")
        self.assertTrue(setup.follower_wanted(sb.pokemmo))      # on before
        make_newer(sb, record_format=2, version="2.0.0")
        self.assertFalse(setup.follower_wanted(sb.pokemmo))

    def test_follow_refuses_once_at_the_start(self):
        sb, _ = self.installed_newer(record_format=2, version="2.0.0")
        before = sb.snapshot()
        r = sb.setup("--follow", check=False, steam=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((r.stdout + r.stderr).count(NEWER), 1)
        self.assertNotIn("Watching", r.stdout)
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_rollback_does_not_edit_a_newer_record(self):
        import updater
        sb, _ = self.installed_newer(record_format=2, version="2.0.0", layout={"from": "2.x"})
        old_record = json.dumps({"version": common.VERSION, "layout": None, "follow": False}).encode()
        before = sb.snapshot()
        updater._restore_layout(sb.pokemmo, old_record)
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_uninstall_also_undoes_files_only_the_newer_version_knows(self):
        sb = self.make()
        mine = sb.home / "settings.conf"            # the player's file the newer version edited
        mine.write_bytes(b"theirs\r\n")
        pristine = sb.snapshot()
        sb.setup()
        new_file = sb.pokemmo / "config" / "pmc-profile.json"   # a file the newer version created
        new_file.write_bytes(b"{}\n")
        common.write_atomic(common.backup_path(mine), mine.read_bytes())
        mine.write_bytes(b"edited by 2.x\n")
        later = sb.home / "later.conf"               # edited by 2.x, then by the player
        later.write_bytes(b"player again\n")
        common.write_atomic(common.backup_path(later), b"player\n")
        files = {str(new_file): {"sha": common.sha(b"{}\n"), "pristine": True, "created": True},
                 str(mine): {"sha": common.sha(b"edited by 2.x\n"), "pristine": True, "created": False},
                 str(later): {"sha": common.sha(b"2.x\n"), "pristine": True, "created": False}}
        rec = json.loads(record_path(sb).read_text(encoding="utf-8"))
        rec["files"].update(files)
        make_newer(sb, record_format=2, version="2.0.0", files=rec["files"])
        r = sb.setup("--uninstall")
        self.assertIn("Left as it is", r.stdout)
        self.assertIn(str(later), r.stdout)
        self.assertEqual(later.read_bytes(), b"player again\n")            # never overwritten
        self.assertTrue(common.backup_path(later).exists())                 # kept for the player
        later.unlink()
        common.backup_path(later).unlink()
        self.assertEqual(diff(pristine, sb.snapshot()), [])

    def test_a_record_in_todays_format_is_uninstalled_as_before(self):
        import uninstall
        sb = self.make()
        sb.setup()
        p = common.Plan(sb.pokemmo)
        p.files[str(sb.home / "not ours")] = {"sha": "0" * 64, "pristine": True, "created": True}
        uninstall.revert_unknown(p)
        self.assertEqual(p.changes, {})

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

    def newer_install(self):
        sb = self.make()
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        make_newer(sb, record_format=2, version="2.0.0")
        return sb

    def test_status_names_the_newer_version_and_never_suggests_an_install(self):
        # `pmc install` refuses a newer record, so pointing the player at it sends them in a circle
        sb = self.newer_install()
        before = sb.snapshot()
        r = self.pmc(sb, "status", check=0)
        self.assertIn(NEWER, r.stdout)
        self.assertNotIn("pmc install", r.stdout + r.stderr)
        self.assertNotIn("out of date", r.stdout)
        j = self.js(self.pmc(sb, "status", "--json", check=0))
        self.assertTrue(j["newer"])
        self.assertEqual([p["id"] for p in j["problems"]], ["newer"])
        self.assertNotIn("pmc install", json.dumps(j))
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_doctor_exits_6_and_says_use_pmc(self):
        sb = self.newer_install()
        before = sb.snapshot()
        r = self.pmc(sb, "doctor", check=6)
        self.assertIn(NEWER, r.stdout + r.stderr)
        self.assertNotIn("pmc install", r.stdout + r.stderr)
        j = self.js(self.pmc(sb, "doctor", "--json", check=6))
        self.assertEqual(j["error"]["code"], "DATA_NEWER")
        self.assertIn(NEWER, j["error"]["message"])
        self.assertTrue(j["data"]["newer"])
        self.assertNotIn("pmc install", json.dumps(j))
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_normal_install_is_not_called_newer(self):
        sb = self.make()
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        self.assertFalse(self.js(self.pmc(sb, "status", "--json", check=0))["newer"])
        self.assertFalse(self.js(self.pmc(sb, "doctor", "--json", check=0))["newer"])
        make_newer(sb, version="9.9.9")       # a newer 1.x in today's format: the updater's rollback case
        self.assertFalse(self.js(self.pmc(sb, "status", "--json", check=0))["newer"])

    def test_the_drift_answer_stays_the_files_truth(self):
        # the remap screen reads binds_current/steam_current as "re-apply": a newer record must not
        # turn them false (re-apply refuses), they stay what the files say
        sb = self.newer_install()
        j = self.js(self.pmc(sb, "status", "--json", check=0))
        self.assertTrue(j["binds_current"])
        self.assertTrue(j["steam_current"])


class NewerRecordUpdateSettings(Base):
    """setup.py --channel / --update-check / --update on a newer install: the real reason, not
    "not installed yet", and nothing changed (no settings written, no update looked up)."""

    def test_settings_and_update_commands_name_the_newer_version(self):
        sb = self.make()
        sb.setup()
        make_newer(sb, record_format=2, version="2.0.0")
        before = sb.snapshot()
        # an address nothing answers: a run that got as far as looking up an update fails differently
        offline = {"POKEMMO_CONTROLLER_UPDATE_BASE": "http://127.0.0.1:9/"}
        for args in (("--channel", "beta"), ("--update-check", "off"), ("--update", "--check"),
                     ("--update", "--yes"), ("--channel", "stable", "--update", "--check")):
            with self.subTest(args=args):
                r = sb.setup(*args, check=False, env=offline)
                out = r.stdout + r.stderr
                self.assertNotEqual(r.returncode, 0, out)
                self.assertIn(NEWER, out)
                self.assertIn("Nothing was changed", out)
                self.assertNotIn("not installed yet", out)
                self.assertNotIn("Update channel:", out)
                self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_newer_1x_in_todays_format_still_changes_settings(self):
        # the updater rolls back over a record a newer 1.x wrote: only record_format decides
        sb = self.make()
        sb.setup()
        make_newer(sb, version="9.9.9")
        r = sb.setup("--channel", "beta")
        self.assertIn("Update channel: beta.", r.stdout)
        self.assertNotIn(NEWER, r.stdout + r.stderr)
        rec = json.loads(record_path(sb).read_text(encoding="utf-8"))
        self.assertEqual(rec["update"]["channel"], "beta")

    def test_with_no_install_it_still_says_install_first(self):
        sb = self.make()
        r = sb.setup("--channel", "beta", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not installed yet", r.stdout + r.stderr)
        self.assertNotIn(NEWER, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
