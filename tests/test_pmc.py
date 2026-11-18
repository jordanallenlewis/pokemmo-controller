"""The command-line path: `pmc` (tools/pmc.py). Sandboxes only: no real PokeMMO or Steam.

The terminal and the remap screen are two views over one engine, so a test here also
fails if either view grows its own writer.
"""
import ast, io, json, subprocess, sys, unittest
from contextlib import redirect_stderr, redirect_stdout

from helpers import ROOT, TOOLS, Sandbox
import common
import pmc
from test_setup import Base


class PMC(Base):
    def pmc(self, sb, *args, steam=True, check=None, stdin=subprocess.DEVNULL, env=None):
        cmd = [sys.executable, str(TOOLS / "pmc.py"), *args, "--pokemmo", str(sb.pokemmo)]
        if steam:
            cmd += ["--steam", str(sb.steam)]
        r = subprocess.run(cmd, env=sb.env(**(env or {})), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=stdin)
        if check is not None and r.returncode != check:
            raise AssertionError(f"pmc {args} exited {r.returncode}, wanted {check}:\n{r.stdout}\n{r.stderr}")
        return r

    def js(self, r):
        return json.loads(r.stdout)    # stdout holds exactly one JSON object

    # ------------------------------------------------------------ version
    def test_version_in_text_and_json(self):
        sb = self.make()
        r = self.pmc(sb, "version", check=0)
        self.assertIn(common.VERSION, r.stdout)
        self.assertEqual(self.js(self.pmc(sb, "version", "--json", check=0))["version"], common.VERSION)

    # ------------------------------------------------------------ status and doctor
    def test_status_before_install_needs_attention_and_writes_nothing(self):
        sb = self.make()
        before = sb.snapshot()
        r = self.pmc(sb, "status", check=5)
        self.assertIn("not installed", r.stdout.lower())
        self.assertIn("pmc install", r.stdout)
        j = self.js(self.pmc(sb, "status", "--json", check=5))
        self.assertFalse(j["installed"])
        self.assertEqual(j["exit"], 5)
        self.assertTrue(j["problems"])
        self.assertSame(before, sb.snapshot())

    def test_status_when_pokemmo_is_missing_exits_3(self):
        sb = self.make()
        r = subprocess.run([sys.executable, str(TOOLS / "pmc.py"), "status", "--json", "--pokemmo", str(sb.root / "nope")],
                           env=sb.env(), capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 3, r.stderr)
        j = json.loads(r.stdout)
        self.assertFalse(j["pokemmo"])
        self.assertEqual(j["exit"], 3)

    def test_status_after_install_is_clean_and_json_fields_are_stable(self):
        sb = self.make()
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        r = self.pmc(sb, "status", check=0)
        self.assertIn("in place", r.stdout)
        j = self.js(self.pmc(sb, "status", "--json", check=0))
        for key in ("version", "pokemmo", "pokemmo_open", "installed", "installed_version", "binds",
                    "steam", "binds_current", "steam_current", "wheel_screen", "custom", "problems", "exit"):
            self.assertIn(key, j)
        self.assertTrue(j["installed"] and j["binds_current"] and j["steam_current"])
        self.assertEqual(j["installed_version"], common.VERSION)
        self.assertEqual(j["problems"], [])

    def test_doctor_names_what_is_wrong_and_how_to_fix_it(self):
        sb = self.make()
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        sb.props.write_bytes(sb.props.read_bytes().replace(b"KEY_UP,AXIS,1,false", b"KEY_UP,AXIS,1,true"))
        r = self.pmc(sb, "doctor", check=5)
        self.assertIn("settings changed", r.stdout)
        self.assertIn("pmc install", r.stdout)
        j = self.js(self.pmc(sb, "doctor", "--json", check=5))
        bad = [c for c in j["checks"] if not c["ok"]]
        self.assertTrue(bad)
        self.assertTrue(all(c["fix"] and c["id"] and c["detail"] for c in bad))
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        self.pmc(sb, "doctor", check=0)

    # ------------------------------------------------------------ install, dry run, check, uninstall
    def test_round_trip_through_pmc_restores_every_byte(self):
        sb = self.make()
        before = sb.snapshot()
        r = self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        self.assertIn(f"Installed v{common.VERSION}", r.stdout)
        installed = sb.snapshot()
        self.assertIn("Already up to date", self.pmc(sb, "install", "--yes", "--no-follow", check=0).stdout)
        self.assertSame(installed, sb.snapshot())
        self.assertIn("Removed", self.pmc(sb, "uninstall", "--yes", check=0).stdout)
        self.assertSame(before, sb.snapshot())

    def test_dry_run_writes_nothing_and_lists_the_files(self):
        sb = self.make()
        before = sb.snapshot()
        r = self.pmc(sb, "install", "--dry-run", "--no-follow", check=0)
        self.assertIn("would change", r.stdout)
        self.assertIn("main.properties", r.stdout)
        j = self.js(self.pmc(sb, "install", "--dry-run", "--json", "--no-follow", check=0))
        self.assertTrue(j["dry_run"])
        self.assertTrue(any(c["path"].endswith("main.properties") and c["action"] == "change" for c in j["changes"]))
        self.assertSame(before, sb.snapshot())

    def test_check_exits_7_while_changes_are_pending_and_0_when_none(self):
        sb = self.make()
        before = sb.snapshot()
        self.pmc(sb, "install", "--check", "--no-follow", check=7)
        self.assertSame(before, sb.snapshot())
        self.pmc(sb, "install", "--yes", "--no-follow", check=0)
        self.pmc(sb, "install", "--check", "--no-follow", check=0)
        self.pmc(sb, "uninstall", "--check", check=7)
        self.pmc(sb, "uninstall", "--yes", check=0)
        self.pmc(sb, "uninstall", "--check", check=0)

    def test_json_install_is_one_object_on_stdout(self):
        sb = self.make()
        j = self.js(self.pmc(sb, "install", "--yes", "--json", "--no-follow", check=0))
        self.assertEqual(j["exit"], 0)
        self.assertTrue(j["ok"])
        self.assertTrue(any("Installed" in line for line in j["log"]))

    def test_pokemmo_not_found_exits_3_and_says_what_to_do(self):
        sb = self.make()
        r = subprocess.run([sys.executable, str(TOOLS / "pmc.py"), "install", "--yes", "--pokemmo", str(sb.root / "nope")],
                           env=sb.env(), capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 3)
        self.assertIn("main.properties", r.stderr)

    def test_a_layout_that_breaks_the_macro_rule_is_refused_with_exit_4(self):
        sb = self.make()
        bad = sb.root / "bad.json"
        bad.write_text(json.dumps({"format": 1, "binds": {"KEY_BAG": {"button": 0, "repeat": 5}},
                                   "wheel": []}), encoding="utf-8")
        before = sb.snapshot()
        r = self.pmc(sb, "install", "--yes", "--no-follow", "--layout", str(bad), check=4)
        self.assertIn("Nothing was changed", r.stderr)
        self.assertSame(before, sb.snapshot())

    def test_bad_usage_exits_2(self):
        sb = self.make()
        self.pmc(sb, "frobnicate", check=2)
        self.pmc(sb, "install", "--yes", "--dry-run", "--check", check=2)

    # ------------------------------------------------------------ asking first
    def test_on_a_terminal_it_shows_the_changes_and_asks_unless_told_not_to(self):
        sb = self.make()
        before = sb.snapshot()
        argv = ["install", "--no-follow", "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam)]
        out, err = io.StringIO(), io.StringIO()
        asked = []
        with redirect_stdout(out), redirect_stderr(err):
            code = pmc.main(argv, interactive=True, ask=lambda q: asked.append(q) or "n")
        self.assertEqual(code, 0)
        self.assertEqual(len(asked), 1)
        self.assertIn("would change", out.getvalue())
        self.assertIn("Nothing was changed", out.getvalue())
        self.assertSame(before, sb.snapshot())

    # ------------------------------------------------------------ one engine
    def test_the_two_views_have_no_writer_of_their_own(self):
        """pmc.py and ui.py only read and hand work to setup.py (and the modules under it).
        A file write, rename or delete in a view is a second engine that can drift."""
        banned_calls = {"write_atomic", "write_text", "write_bytes", "commit", "save_state", "put", "delete",
                        "rmtree", "copyfile", "set_props"}
        banned_on_os = {"replace", "rename", "remove", "unlink", "copy", "move", "makedirs", "mkdir"}
        for name in ("pmc.py", "ui.py"):
            tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                called = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                owner = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
                if owner in ("os", "shutil") and called in banned_on_os and not (name == "ui.py" and called == "unlink"):
                    self.fail(f"{name} line {node.lineno}: a view must not write ({owner}.{called})")  # ui's unlink: its temp copy
                self.assertNotIn(called, banned_calls, f"{name} line {node.lineno}: a view must not write ({called})")
                if called == "open" and len(node.args) > 1:
                    mode = node.args[1]
                    self.assertFalse(isinstance(mode, ast.Constant) and any(c in str(mode.value) for c in "wax+"),
                                     f"{name} line {node.lineno}: a view must not open a file for writing")

    def test_the_two_views_share_one_status(self):
        import ui, status
        sb = self.make()
        self.assertIs(ui.status_mod, status)
        a = ui.App(pokemmo=str(sb.pokemmo), steam=str(sb.steam), env=sb.env())
        want = status.summary(str(sb.pokemmo), str(sb.steam), False)
        got = a.status(str(sb.pokemmo))
        self.assertEqual(got, {k: want[k] for k in got})


if __name__ == "__main__":
    unittest.main()
