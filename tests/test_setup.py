"""Install, update and uninstall round trips in sandboxes (no real PokeMMO or Steam).

Run:  python -m unittest discover -s tests -v
"""
import os, stat, subprocess, sys, unittest
from pathlib import Path
from unittest import mock

from helpers import ROOT, USER_PAD, Sandbox, shortcuts, GAME
import common, apply_native, install_wheel, setup as setup_mod, platforms


def diff(a, b):
    keys = sorted(set(a) | set(b))
    return [k for k in keys if a.get(k, "<missing>") != b.get(k, "<missing>")]


class Base(unittest.TestCase):
    def make(self, **kw):
        sb = Sandbox(**kw)
        self.addCleanup(sb.cleanup)
        return sb

    def assertSame(self, before, after):
        self.assertEqual(diff(before, after), [], "files differ from the snapshot")


class RoundTrip(Base):
    def test_install_rerun_uninstall_restores_every_byte(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup()
        self.assertIn(f"Installed v{common.VERSION}", r.stdout)
        text = sb.props.read_text(encoding="utf-8")
        self.assertIn("Xbox Series X Controller;KEY_UP,AXIS,1,false", text)
        self.assertIn("8BitDo Pro 2;", text)                  # pad from PokeMMO's log
        self.assertIn(USER_PAD, text)                         # hand-made map kept
        self.assertIn("\\#SettingsController_SteamController;", text)
        self.assertIn("client.input.controllers.enable_native_support=true", text)
        self.assertNotIn("\n", sb.props.read_bytes().replace(b"\r\n", b"").decode())  # CRLF kept
        self.assertTrue((sb.cfg / "pokemmo" / "controller_xboxone.vdf").exists())
        self.assertIn('"pokemmo"', (sb.cfg / "configset_controller_xboxone.vdf").read_text())
        self.assertNotIn(b"\r\n", (sb.cfg / "configset_controller_xboxone.vdf").read_bytes())  # LF kept
        sc = install_wheel.read_shortcuts((sb.steam / "userdata/12345/config/shortcuts.vdf").read_bytes())
        self.assertEqual(sorted(sc), ["0", "2", "3"])  # no clash with existing keys
        self.assertEqual(sc["2"]["AppName"], "Other")
        self.assertTrue((sb.steam / "userdata/67890/config/shortcuts.vdf").exists())
        self.assertFalse((sb.steam / "userdata/0/config").exists())
        installed = sb.snapshot()

        r = sb.setup()
        self.assertIn("Already up to date", r.stdout)
        self.assertSame(installed, sb.snapshot())

        r = sb.setup("--uninstall")
        self.assertIn("Removed", r.stdout)
        self.assertSame(before, sb.snapshot())

        r = sb.setup("--uninstall")
        self.assertIn("Nothing to undo", r.stdout)
        self.assertSame(before, sb.snapshot())

    def test_spaces_and_non_ascii_paths(self):
        sb = self.make(name="Pokémon Täst 測試 folder")
        before = sb.snapshot()
        r = sb.setup()
        self.assertIn("Installed", r.stdout)
        sb.setup("--uninstall")
        self.assertSame(before, sb.snapshot())

    def test_lf_file_without_final_newline(self):
        sb = self.make(crlf=False, props="a=1\nb=2")
        before = sb.snapshot()
        sb.setup()
        self.assertNotIn(b"\r", sb.props.read_bytes())
        sb.setup("--uninstall")
        self.assertSame(before, sb.snapshot())

    def test_empty_and_corrupt_main_properties(self):
        for props in ("", b"\x00\xff\xfe garbage \x81\n=\n\\\n"):
            sb = self.make(props=props)
            before = sb.snapshot()
            sb.setup()
            self.assertIn(b"KEY_RING_FOCUS", sb.props.read_bytes())
            sb.setup("--uninstall")
            self.assertSame(before, sb.snapshot())

    def test_without_steam(self):
        sb = self.make(steam=False)
        before = sb.snapshot()
        r = sb.setup(steam=False)
        self.assertIn("Steam not found", r.stdout)
        self.assertIn("Start PokeMMO and play", r.stdout)
        self.assertNotIn("client.controls.gdx.codex=42", sb.props.read_text())  # no wheel keys
        sb.setup("--uninstall", steam=False)
        self.assertSame(before, sb.snapshot())

    def test_no_wheel_leaves_steam_alone(self):
        sb = self.make()
        steam_before = {k: v for k, v in sb.snapshot().items() if k.startswith("Steam/")}
        sb.setup("--no-wheel")
        self.assertEqual(steam_before, {k: v for k, v in sb.snapshot().items() if k.startswith("Steam/")})


class Failures(Base):
    def test_pokemmo_not_installed(self):
        sb = self.make(props=None)
        before = sb.snapshot()
        r = sb.setup(check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("main.properties", r.stderr)
        self.assertSame(before, sb.snapshot())

    def test_read_only_main_properties_changes_nothing(self):
        sb = self.make()
        os.chmod(sb.props, stat.S_IREAD)
        before = sb.snapshot()
        r = sb.setup(check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("read-only", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertSame(before, sb.snapshot())

    def test_corrupt_shortcuts_file_is_left_alone(self):
        sb = self.make()
        bad = sb.steam / "userdata/12345/config/shortcuts.vdf"
        bad.write_bytes(b"\x00shortcuts\x00\x09broken")
        before = sb.snapshot()
        r = sb.setup()
        self.assertIn("Could not read", r.stdout)
        self.assertEqual(bad.read_bytes(), b"\x00shortcuts\x00\x09broken")
        sb.setup("--uninstall")
        self.assertSame(before, sb.snapshot())

    def test_interrupted_install_leaves_whole_files_and_recovers(self):
        """Ctrl-C between file writes: every file is old or new, never half; rerun and undo work."""
        for stop_at in (1, 3, 6, 12):
            sb = self.make()
            before = sb.snapshot()
            calls = {"n": 0}
            real = common.write_atomic

            def flaky(path, data):
                calls["n"] += 1
                if calls["n"] == stop_at:
                    raise KeyboardInterrupt
                return real(path, data)

            argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--no-follow"]
            with mock.patch.dict(os.environ, sb.env()), mock.patch.object(common, "write_atomic", flaky), \
                    mock.patch.object(sys, "argv", argv), mock.patch("builtins.print"):
                with self.assertRaises(SystemExit):
                    setup_mod.main()
            self.assertFalse([p for p in sb.root.rglob("*.tmp")], "temp files left behind")
            sb.setup()
            sb.setup("--uninstall")
            self.assertSame(before, sb.snapshot())

    def test_atomic_write_keeps_old_file_on_interrupt(self):
        sb = self.make()
        old = sb.props.read_bytes()
        with mock.patch.object(common.os, "replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                common.write_atomic(sb.props, b"new")
        self.assertEqual(sb.props.read_bytes(), old)
        self.assertEqual(list(sb.props.parent.glob("*.tmp")), [])

    def test_refuses_while_pokemmo_runs(self):
        sb = self.make()
        before = sb.snapshot()
        argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--no-follow"]
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(sys, "argv", argv), mock.patch.object(platforms, "game_size", return_value=None), \
                mock.patch.object(platforms, "pokemmo_running", return_value=True), mock.patch("builtins.print"):
            with self.assertRaises(SystemExit) as cm:
                setup_mod.main()
        self.assertIn("PokeMMO is open", str(cm.exception.code))
        self.assertSame(before, sb.snapshot())

    def test_never_closes_steam_while_a_game_runs(self):
        sb = self.make()
        before = sb.snapshot()
        argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--no-follow"]
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(sys, "argv", argv), mock.patch.object(platforms, "game_size", return_value=None), \
                mock.patch.object(platforms, "steam_running", return_value=True), \
                mock.patch.object(platforms, "steam_game_running", return_value=440), \
                mock.patch.object(subprocess, "Popen") as popen, mock.patch("builtins.print"):
            with self.assertRaises(SystemExit) as cm:
                setup_mod.main()
        self.assertIn("Steam game is running", str(cm.exception.code))
        popen.assert_not_called()
        self.assertSame(before, sb.snapshot())

    def test_steam_restarted_even_when_install_fails(self):
        sb = self.make()
        argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--no-follow"]
        running = iter([True] + [False] * 10)
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(sys, "argv", argv), mock.patch.object(platforms, "game_size", return_value=None), \
                mock.patch.object(platforms, "steam_running", side_effect=lambda: next(running)), \
                mock.patch.object(setup_mod.time, "sleep"), \
                mock.patch.object(common, "write_atomic", side_effect=PermissionError(13, "denied", "x")), \
                mock.patch.object(subprocess, "Popen") as popen, mock.patch("builtins.print"):
            with self.assertRaises(SystemExit):
                setup_mod.main()
        cmds = [c.args[0] for c in popen.call_args_list]
        self.assertEqual(len(cmds), 2, cmds)  # close, then start again
        self.assertIn("osascript" if platforms.MAC else "-shutdown", cmds[0])
        self.assertNotIn("-shutdown", cmds[1])

    def test_up_to_date_does_not_touch_steam(self):
        sb = self.make()
        sb.setup()
        argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--no-follow"]
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(sys, "argv", argv), mock.patch.object(platforms, "game_size", return_value=None), \
                mock.patch.object(platforms, "steam_running", return_value=True), \
                mock.patch.object(subprocess, "Popen") as popen, mock.patch("builtins.print"):
            setup_mod.main()
        popen.assert_not_called()


class UserChanges(Base):
    def test_uninstall_keeps_changes_made_after_install(self):
        sb = self.make()
        sb.setup()
        text = sb.props.read_text(encoding="utf-8")
        # PokeMMO rewrote the file: new setting, a pad rebound by hand, a pad bound by hand
        text = text.replace("client.ui.theme=dark", "client.ui.theme=light\nclient.new.setting=1")
        text = text.replace("Xbox 360 Controller;KEY_UP,AXIS,1,false", "Xbox 360 Controller;KEY_UP,AXIS,1,true")
        text = text.replace("client.controls.controller_input_maps_gdx_2=",
                            "client.controls.controller_input_maps_gdx_2=Mine;KEY_A,BUTTON,7|")
        sb.props.write_text(text, encoding="utf-8")
        # Steam rewrote a configset and saved another app
        cs = sb.cfg / "configset_controller_xboxone.vdf"
        cs.write_text(cs.read_text()[:-2] + '\t"999"\n\t{\n\t\t"template"\t\t"x"\n\t}\n}\n')
        sb.setup("--uninstall")
        after = sb.props.read_text(encoding="utf-8")
        self.assertIn("client.ui.theme=light", after)
        self.assertIn("client.new.setting=1", after)
        self.assertIn("Xbox 360 Controller;KEY_UP,AXIS,1,true", after)   # rebound by hand: kept
        self.assertIn("Mine;KEY_A,BUTTON,7", after)
        self.assertIn("Xbox One S Controller;KEY_Y,BUTTON,3;KEY_A,BUTTON,0", after)  # original back
        self.assertIn(USER_PAD, after)
        self.assertNotIn("Xbox Series X Controller", after)
        self.assertNotIn("enable_native_support", after)
        self.assertIn("client.controls.gdx.codex=0", after)
        cs_after = cs.read_text()
        self.assertIn('"999"', cs_after)
        self.assertNotIn('"pokemmo"', cs_after)
        self.assertEqual(list(sb.root.rglob("*" + common.SUFFIX)), [])
        self.assertFalse((sb.pokemmo / "config" / common.STATE_NAME).exists())

    def test_existing_pokemmo_shortcut_and_layout_are_kept(self):
        sb = self.make()
        sc = sb.steam / "userdata/12345/config/shortcuts.vdf"
        sc.write_bytes(shortcuts({"0": dict(GAME, AppName="PokeMMO")}))
        mine = sb.cfg / "pokemmo" / "controller_xboxone.vdf"
        mine.parent.mkdir()
        mine.write_text('"controller_mappings"\n{\n\t"title"\t\t"my own"\n}\n')
        cs = sb.cfg / "configset_controller_xboxone.vdf"
        cs.write_text(cs.read_text()[:-2] + '\t"pokemmo"\n\t{\n\t\t"workshop"\t\t"1"\n\t}\n}\n')
        before = sb.snapshot()
        sb.setup()
        self.assertEqual(len(install_wheel.read_shortcuts(sc.read_bytes())), 1)
        self.assertIn("native + right-stick wheel", mine.read_text())
        # Steam saves another app after the install, so the exact restore is off for this file
        cs.write_text(cs.read_text().replace('"220"', '"221"'))
        sb.setup("--uninstall")
        self.assertEqual(len(install_wheel.read_shortcuts(sc.read_bytes())), 1)  # yours stays
        self.assertIn("my own", mine.read_text())
        self.assertIn('"workshop"\t\t"1"', cs.read_text())
        after = sb.snapshot()
        self.assertEqual(diff(before, after), ["Steam/steamapps/common/Steam Controller Configs/12345/config/configset_controller_xboxone.vdf"])

    def test_switch_choice_is_remembered(self):
        sb = self.make()
        sb.setup("--switch-positional")
        sb.setup()
        text = sb.props.read_text(encoding="utf-8")
        self.assertIn("Nintendo Switch Pro Controller;KEY_UP,AXIS,1,false;KEY_DOWN,AXIS,1,true;"
                      "KEY_LEFT,AXIS,0,false;KEY_RIGHT,AXIS,0,true;KEY_A,BUTTON,0", text)
        sb.setup("--switch-labels")
        self.assertIn("KEY_RIGHT,AXIS,0,true;KEY_A,BUTTON,1", sb.props.read_text(encoding="utf-8"))


class Updates(Base):
    def test_update_message_and_dropped_names(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        state_file = sb.pokemmo / "config" / common.STATE_NAME
        import json
        st = json.loads(state_file.read_text())
        st["version"] = "1.0.5"
        st["names"].append("Old Pad")
        state_file.write_text(json.dumps(st))
        text = sb.props.read_text(encoding="utf-8").replace(
            "client.controls.controller_input_maps_gdx_2=",
            "client.controls.controller_input_maps_gdx_2=" + apply_native.encode_one("Old Pad") + "|")
        sb.props.write_text(text, encoding="utf-8")
        r = sb.setup()
        self.assertIn(f"Updated from v1.0.5 to v{common.VERSION}", r.stdout)
        self.assertNotIn("Old Pad", sb.props.read_text(encoding="utf-8"))
        sb.setup("--uninstall")
        self.assertNotIn("KEY_RING_FOCUS", sb.props.read_text(encoding="utf-8"))
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_stale_backups_from_old_uninstall_are_replaced(self):
        sb = self.make()
        bak = common.backup_path(sb.props)
        bak.write_text("client.ui.theme=ancient\n")  # left behind by v1.0.0's uninstaller
        before = sb.snapshot()
        sb.setup()
        self.assertEqual(bak.read_bytes(), before["Poke MMO/config/main.properties"])
        sb.setup("--uninstall")
        del before["Poke MMO/config/main.properties" + common.SUFFIX]
        self.assertSame(before, sb.snapshot())


def legacy_tools(ref):
    """Check out tools/ from an older release into a temp folder (needs git history)."""
    import tempfile
    try:
        files = subprocess.run(["git", "ls-tree", "--name-only", ref, "tools/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None
    d = Path(tempfile.mkdtemp(prefix="pmc-legacy-"))
    (d / "tools").mkdir()
    for f in files:
        if f.endswith(".py"):
            data = subprocess.run(["git", "show", f"{ref}:{f}"], cwd=ROOT, capture_output=True, check=True).stdout
            (d / f).write_bytes(data)
    return d


class Legacy(Base):
    def upgrade_from(self, ref, scripts, windows_only=False):
        if windows_only and not platforms.WINDOWS:
            self.skipTest(f"{ref} ran on Windows only")
        if sys.version_info < (3, 10):
            self.skipTest(f"{ref} needed Python 3.10 (Path.write_text(newline=)); fixed since")
        old = legacy_tools(ref)
        if old is None:
            self.skipTest("git history not available")
        self.addCleanup(__import__("shutil").rmtree, old, True)
        sb = self.make()
        before = sb.snapshot()
        for s in scripts:
            # v1.0.0 asked `tasklist` whether Steam runs (no test switch): answer "no"
            shim = ("import runpy, subprocess, sys; real = subprocess.run\n"
                    "subprocess.run = lambda a, *k, **kw: subprocess.CompletedProcess(a, 0, '', '') "
                    "if a and a[0] == 'tasklist' else real(a, *k, **kw)\n"
                    "sys.argv = sys.argv[1:]; sys.path.insert(0, str(__import__('pathlib').Path(sys.argv[0]).parent))\n"
                    "runpy.run_path(sys.argv[0], run_name='__main__')")
            r = subprocess.run([sys.executable, "-c", shim, str(old / "tools" / s), "--pokemmo", str(sb.pokemmo)]
                               + (["--steam", str(sb.steam)] if s != "apply_native.py" else []),
                               env=sb.env(), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        r = sb.setup()
        self.assertIn(f"Updated from an earlier version to v{common.VERSION}", r.stdout)
        text = sb.props.read_text(encoding="utf-8")
        self.assertTrue((sb.cfg / "pokemmo" / "controller_ps5.vdf").exists())  # new pad types added
        self.assertIn(USER_PAD, text)  # v1.0.0 dropped it; the update brings it back
        self.assertEqual(text.count("Xbox Series X Controller;"), 1)
        r = sb.setup()
        self.assertIn("Already up to date", r.stdout)
        sb.setup("--uninstall")
        after = sb.snapshot()
        changed = diff(before, after)
        # v1.0.0 kept no record, so main.properties comes back by merge, not byte for byte
        self.assertEqual([c for c in changed if not c.endswith("main.properties")], [])
        self.assertNotIn("KEY_RING_FOCUS", sb.props.read_text(encoding="utf-8"))
        self.assertIn(USER_PAD, sb.props.read_text(encoding="utf-8"))

    def test_upgrade_from_v1_0_0(self):
        self.upgrade_from("v1.0.0", ["apply_native.py", "install_wheel.py"], windows_only=True)

    def test_upgrade_from_one_command_installer(self):
        self.upgrade_from("d78c07b", ["setup.py"])


if __name__ == "__main__":
    unittest.main()


class DryRun(Base):
    def test_dry_run_changes_nothing_and_names_the_files(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--dry-run")
        self.assertIn("Dry run", r.stdout)
        self.assertIn("would change:", r.stdout)
        self.assertIn("would create:", r.stdout)
        self.assertIn("main.properties", r.stdout)
        self.assertNotIn("Installed", r.stdout)
        self.assertSame(before, sb.snapshot())  # no record, no backup, no file

    def test_dry_run_after_install_and_uninstall(self):
        sb = self.make()
        sb.setup()
        installed = sb.snapshot()
        self.assertIn("Nothing would change", sb.setup("--dry-run").stdout)
        r = sb.setup("--dry-run", "--uninstall")
        self.assertIn("would", r.stdout)
        self.assertSame(installed, sb.snapshot())
        sb.setup("--uninstall")

    def test_dry_run_works_while_pokemmo_is_open(self):
        sb = self.make()
        before = sb.snapshot()
        argv = ["setup.py", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam), "--dry-run"]
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(sys, "argv", argv), mock.patch.object(platforms, "game_size", return_value=None), \
                mock.patch.object(platforms, "pokemmo_running", return_value=True), mock.patch("builtins.print"):
            setup_mod.main()  # no SystemExit: reading is safe with the game open
        self.assertSame(before, sb.snapshot())
