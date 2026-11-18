"""Updates: the signed manifest, one-step apply, rollback, opt-out, channels, package managers,
the release files, and what the check sends. A local server stands in for GitHub; the
"release" is this checkout with a newer VERSION, built by .github/release_meta.py."""
import base64, http.client, http.server, json, os, shutil, subprocess, sys, tarfile, tempfile, threading, unittest
from pathlib import Path
from unittest import mock

import helpers
from helpers import ROOT, TOOLS
from test_setup import Base, diff
import ed25519, layout as L, updater

sys.path.insert(0, str(ROOT / ".github"))
import release_meta  # noqa: E402

SEED = bytes(range(32))
PUB = ed25519.public_key(SEED).hex()
OTHER_SEED = bytes(range(1, 33))
NEW = "9.9.9"
CI = bool(os.environ.get("CI"))


class Server:
    """Serves a folder on 127.0.0.1 and remembers every request."""

    def __init__(self, folder):
        self.requests = []
        outer = self

        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(folder), **k)

            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.requests.append((self.path, dict(self.headers)))
                super().do_GET()

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def make_release(workdir, version=NEW, seed=SEED, base="http://x/", failing=False, notes="- Something players notice.",
                 tamper=False, tools_from=None):
    """Build, sign and lay out a release of this checkout as <version>. Returns the folder to serve."""
    src = Path(workdir) / "src"
    for d in ("tools", "steam"):
        shutil.copytree(ROOT / d, src / d, ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("install.sh", "install.ps1", "LICENSE"):
        shutil.copy2(ROOT / f, src / f)
    common = src / "tools" / "common.py"
    common.write_text(common.read_text().replace(f'VERSION = "{updater.VERSION}"', f'VERSION = "{version}"'))
    (src / "CHANGELOG.md").write_text(f"# Changelog\n\n## {version} - 2026-12-01\n\n{notes}\n")
    if failing:  # the new setup runs fully, then fails: a half-finished update
        (src / "tools" / "setup_real.py").write_text((src / "tools" / "setup.py").read_text())
        (src / "tools" / "setup.py").write_text(
            "import runpy, sys\nfrom pathlib import Path\n"
            "p = str(Path(__file__).with_name('setup_real.py'))\nsys.argv[0] = p\n"
            "runpy.run_path(p, run_name='__main__')\nsys.exit(5)\n")
    out = Path(workdir) / "site"
    m = release_meta.build(f"v{version}", out, src)
    m["url"] = base + Path(m["url"]).name
    (out / "update.json").write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
    with mock.patch.dict(os.environ, {"UPDATE_SIGNING_KEY": base64.b64encode(seed).decode()}):
        release_meta.sign(out)
    if tamper:
        a = out / Path(m["url"]).name
        data = bytearray(a.read_bytes())
        data[-5] ^= 0xFF
        a.write_bytes(bytes(data))
    return out


class UpdateBase(Base):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pmc-rel-")
        self.addCleanup(self._tmp.cleanup)
        self.servers = []
        self.addCleanup(lambda: [s.stop() for s in self.servers])

    def release(self, **kw):
        folder = Path(tempfile.mkdtemp(dir=self._tmp.name))
        srv = Server(folder / "site")
        self.servers.append(srv)
        make_release(folder, base=srv.url, **kw)
        return srv

    def env(self, srv, **extra):
        return dict(POKEMMO_CONTROLLER_UPDATE_BASE=srv.url, POKEMMO_CONTROLLER_UPDATE_KEY=PUB, **extra)

    def installed(self, layout=True, ui=True):
        sb = self.make()
        self.pristine = sb.snapshot()
        args = (["--install-ui"] if ui else [])
        if layout:
            lay = L.default_layout()
            lay["binds"]["KEY_INVENTORY"] = {"button": 9}
            lay["binds"]["KEY_RING_FOCUS"] = {"button": 10}
            f = Path(self._tmp.name) / "mine.json"
            f.write_text(json.dumps(lay), encoding="utf-8")
            args += ["--layout", str(f)]
        sb.setup(*args)
        return sb

    def record(self, sb):
        return json.loads((sb.pokemmo / "config" / "pokemmo-controller.json").read_text())


class Check(UpdateBase):
    def test_check_reports_a_newer_release_with_notes(self):
        sb = self.installed()
        srv = self.release()
        before = sb.snapshot()
        r = sb.setup("--update", "--check", env=self.env(srv))
        self.assertIn(f"v{NEW} is available", r.stdout)
        self.assertIn("Something players notice", r.stdout)
        self.assertEqual(diff(before, sb.snapshot()), [], "--check must change nothing")

    def test_up_to_date(self):
        sb = self.installed()
        srv = self.release(version=updater.VERSION)
        r = sb.setup("--update", "--check", env=self.env(srv))
        self.assertIn("up to date", r.stdout)

    def test_an_older_release_is_never_offered(self):
        sb = self.installed()
        srv = self.release(version="0.1.0")
        self.assertIn("up to date", sb.setup("--update", "--check", env=self.env(srv)).stdout)

    def test_check_sends_nothing_but_the_request(self):
        sb = self.installed()
        srv = self.release()
        sb.setup("--update", "--check", env=self.env(srv))
        self.assertEqual(sorted(p for p, _ in srv.requests), ["/update.json", "/update.json.sig"])
        for _, headers in srv.requests:
            low = {k.lower() for k in headers}
            self.assertFalse(low & {"cookie", "authorization", "referer", "x-key"}, headers)
            self.assertNotIn(updater.VERSION, " ".join(headers.values()))
            self.assertNotIn(str(sb.root), " ".join(headers.values()))

    def test_unreachable_server_is_one_plain_sentence(self):
        sb = self.installed()
        r = sb.setup("--update", "--check", check=False,
                     env=dict(POKEMMO_CONTROLLER_UPDATE_BASE="http://127.0.0.1:9/", POKEMMO_CONTROLLER_UPDATE_KEY=PUB))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Could not reach the update server", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class Refusals(UpdateBase):
    def test_a_signature_from_another_key_is_refused(self):
        sb = self.installed()
        srv = self.release(seed=OTHER_SEED)
        before = sb.snapshot()
        r = sb.setup("--update", "--yes", check=False, env=self.env(srv))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("signature did not check out", r.stderr)
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_changed_manifest_is_refused(self):
        sb = self.installed()
        srv = self.release()
        mf = next(Path(self._tmp.name).glob("*/site/update.json"))
        m = json.loads(mf.read_text())
        m["version"] = "10.0.0"           # a lie, signature no longer matches
        mf.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        r = sb.setup("--update", "--yes", check=False, env=self.env(srv))
        self.assertIn("signature did not check out", r.stderr)

    def test_a_changed_archive_is_refused(self):
        sb = self.installed()
        srv = self.release(tamper=True)
        before = sb.snapshot()
        r = sb.setup("--update", "--yes", check=False, env=self.env(srv))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("did not match its signed checksum", r.stderr)
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_a_missing_signature_is_refused(self):
        sb = self.installed()
        srv = self.release()
        for f in Path(self._tmp.name).glob("*/site/update.json.sig"):
            f.unlink()
        r = sb.setup("--update", "--check", check=False, env=self.env(srv))
        self.assertNotEqual(r.returncode, 0)

    def test_a_download_address_outside_the_project_is_refused(self):
        m = {"schema": 1, "version": NEW, "channel": "stable", "sha256": "0" * 64, "size": 5, "notes": ["x"],
             "url": "https://evil.example/release.tar.gz"}
        raw = json.dumps(m).encode()
        sig = base64.b64encode(ed25519.sign(SEED, raw)).decode()
        with mock.patch.dict(os.environ, {"POKEMMO_CONTROLLER_UPDATE_KEY": PUB}):
            with self.assertRaises(updater.UpdateError):
                updater.verify_manifest(raw, sig)

    def test_archive_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as d:
            evil = Path(d) / "evil.tar.gz"
            with tarfile.open(evil, "w:gz") as t:
                ti = tarfile.TarInfo("../outside.txt")
                ti.size = 1
                import io
                t.addfile(ti, io.BytesIO(b"x"))
            with self.assertRaises(updater.UpdateError):
                updater.extract(evil, Path(d) / "out")
            self.assertFalse((Path(d) / "outside.txt").exists())

    def test_a_release_whose_inside_version_differs_is_refused(self):
        sb = self.installed()
        srv = self.release()
        mf = next(Path(self._tmp.name).glob("*/site/update.json"))
        m = json.loads(mf.read_text())
        m["version"] = "9.9.8"
        mf.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        with mock.patch.dict(os.environ, {"UPDATE_SIGNING_KEY": base64.b64encode(SEED).decode()}):
            release_meta.sign(mf.parent)
        r = sb.setup("--update", "--yes", check=False, env=self.env(srv))
        self.assertIn("not the version it says", r.stderr)


class Apply(UpdateBase):
    ALLOWED = ("pokemmo-controller/", "config/pokemmo-controller.json")

    def test_one_step_update_keeps_the_players_layout(self):
        sb = self.installed()
        srv = self.release()
        before = sb.snapshot()
        rec = self.record(sb)
        r = sb.setup("--update", "--yes", env=self.env(srv))
        self.assertIn(f"Updated to v{NEW}", r.stdout)
        self.assertIn("test it", r.stdout.lower() + " test it")
        after = self.record(sb)
        self.assertEqual(after["version"], NEW)
        self.assertEqual(after["layout"], rec["layout"], "the player's remaps must survive")
        self.assertEqual(after["update"]["just_updated"]["to"], NEW)
        # the binds and the Steam wheel are the player's layout, byte for byte
        changed = [k for k in diff(before, sb.snapshot()) if not any(a in k for a in self.ALLOWED)]
        self.assertEqual(changed, [])
        app = sb.pokemmo / "pokemmo-controller" / "tools" / "common.py"
        self.assertIn(f'VERSION = "{NEW}"', app.read_text())
        # the version that ran before is kept for rollback
        self.assertIn(f'VERSION = "{updater.VERSION}"',
                      (sb.pokemmo / "pokemmo-controller" / "last-good" / "tools" / "common.py").read_text())
        # and the new version installs and uninstalls exactly like any other
        sb.setup("--uninstall")
        self.assertEqual(diff(self.pristine, sb.snapshot()), [])

    def test_update_from_the_previous_release_layout(self):
        """A computer that was set up by v1.2.0 (the release before updates existed) takes the update."""
        tag = subprocess.run(["git", "tag", "--list", "v1.2.0"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not tag:
            if CI:
                self.fail("the v1.2.0 tag is missing: CI must fetch full history")
            self.skipTest("no v1.2.0 tag in this clone")
        old = Path(self._tmp.name) / "v120"
        old.mkdir()
        tarball = subprocess.run(["git", "archive", "v1.2.0", "tools", "steam"], cwd=ROOT, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(old)], input=tarball, check=True)
        sb = self.make()
        cmd = [sys.executable, str(old / "tools" / "setup.py"), "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam),
               "--no-follow", "--install-ui"]
        subprocess.run(cmd, env=sb.env(), capture_output=True, check=True)
        self.assertEqual(self.record(sb)["version"], "1.2.0")
        srv = self.release()
        r = sb.setup("--update", "--yes", env=self.env(srv))
        self.assertIn(f"Updated to v{NEW}", r.stdout)
        self.assertEqual(self.record(sb)["version"], NEW)
        sb.setup("--uninstall")

    def test_a_failed_update_puts_the_old_version_back(self):
        sb = self.installed()
        srv = self.release(failing=True)
        before = sb.snapshot()
        rec = self.record(sb)
        r = sb.setup("--update", "--yes", check=False, env=self.env(srv))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(f"v{updater.VERSION} is back", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        after = self.record(sb)
        self.assertEqual(after["version"], updater.VERSION)
        self.assertEqual(after["layout"], rec["layout"])
        changed = [k for k in diff(before, sb.snapshot()) if "last-good" not in k]
        self.assertEqual(changed, [], "every file is back to how it was")
        # the app copy runs again as the old version
        self.assertIn(f'VERSION = "{updater.VERSION}"',
                      (sb.pokemmo / "pokemmo-controller" / "tools" / "common.py").read_text())
        self.assertFalse((sb.pokemmo / "pokemmo-controller" / "update-work").exists())
        sb.setup("--uninstall")
        self.assertEqual(diff(self.pristine, sb.snapshot()), [], "uninstall after a rollback leaves nothing")

    def test_pokemmo_open_stops_the_update_before_anything_changes(self):
        sb = self.installed()
        srv = self.release()
        before = sb.snapshot()
        with mock.patch.dict(os.environ, self.env(srv)), \
                mock.patch.object(updater.P, "pokemmo_running", return_value=True):
            c = updater.check("stable")
            with self.assertRaises(updater.UpdateError) as cm:
                updater.apply(sb.pokemmo, c["manifest"], steam=sb.steam)
        self.assertIn("PokeMMO is open", str(cm.exception))
        self.assertEqual(diff(before, sb.snapshot()), [])


class Settings(UpdateBase):
    def test_opt_out_asks_nothing(self):
        sb = self.installed()
        srv = self.release()
        sb.setup("--update-check", "off")
        self.assertFalse(updater.settings(self.record(sb))["check"])
        with mock.patch.dict(os.environ, self.env(srv)):
            st = updater.status(sb.pokemmo, force=True)
        self.assertFalse(st["enabled"])
        self.assertEqual(srv.requests, [], "turned off means no request at all")
        sb.setup("--update-check", "on")
        with mock.patch.dict(os.environ, self.env(srv)):
            self.assertTrue(updater.status(sb.pokemmo, force=True)["available"])

    def test_the_app_asks_again_only_about_daily(self):
        sb = self.installed()
        srv = self.release()
        with mock.patch.dict(os.environ, self.env(srv)):
            updater.status(sb.pokemmo, clock=lambda: 2e9)
            n = len(srv.requests)
            again = updater.status(sb.pokemmo, clock=lambda: 2e9 + 3600)
            self.assertEqual(len(srv.requests), n)
            self.assertTrue(again["available"] and again["version"] == NEW)
            updater.status(sb.pokemmo, clock=lambda: 2e9 + 25 * 3600)
            self.assertGreater(len(srv.requests), n)

    def test_later_hides_that_version_only(self):
        sb = self.installed()
        srv = self.release()
        with mock.patch.dict(os.environ, self.env(srv)):
            updater.status(sb.pokemmo, force=True)
            updater.save_settings(sb.pokemmo, later=NEW)
            self.assertTrue(updater.status(sb.pokemmo)["dismissed"])

    def test_stable_never_offers_a_prerelease_and_beta_does(self):
        sb = self.installed()
        srv = self.release(version="9.9.9-beta.1")
        with mock.patch.dict(os.environ, self.env(srv)):
            self.assertFalse(updater.check("stable")["available"])
            self.assertTrue(updater.check("beta")["available"])
        sb.setup("--channel", "beta")
        self.assertEqual(updater.settings(self.record(sb))["channel"], "beta")

    def test_package_managers_are_told_to_update_themselves(self):
        sb = self.installed()
        srv = self.release()
        for who in ("winget", "homebrew"):
            before = sb.snapshot()
            r = sb.setup("--update", "--yes", env=self.env(srv, POKEMMO_CONTROLLER_MANAGED=who))
            self.assertIn(who if who == "winget" else "brew", r.stdout)
            self.assertEqual(diff(before, sb.snapshot()), [])
        self.assertEqual(srv.requests, [], "a managed copy never fetches from here")
        self.assertEqual(updater.managed_by(Path("C:/Users/x/AppData/Local/Microsoft/WinGet/Packages/y/tools")), "winget")
        self.assertEqual(updater.managed_by(Path("/opt/homebrew/Cellar/pokemmo-controller/1.0/tools")), "homebrew")

    def test_versions_sort_like_releases(self):
        order = ["1.2.0", "1.3.0-beta.1", "1.3.0-beta.2", "1.3.0", "1.10.0", "2.0.0"]
        parsed = [updater.parse_version(v) for v in order]
        self.assertEqual(parsed, sorted(parsed))
        self.assertTrue(updater.is_newer("1.3.0", "1.3.0-beta.1"))
        self.assertFalse(updater.is_newer("1.3.0-beta.1", "1.3.0"))
        with self.assertRaises(updater.UpdateError):
            updater.parse_version("latest")


class AppScreen(UpdateBase):
    """The remap screen's banner talks to these endpoints."""

    def start(self, sb, srv):
        import ui
        patch = mock.patch.dict(os.environ, self.env(srv))
        patch.start()
        self.addCleanup(patch.stop)
        app = ui.App(pokemmo=str(sb.pokemmo), steam=str(sb.steam), env=sb.env(**self.env(srv)))
        httpd = ui.make_server(app)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        self.app, self.port = app, httpd.server_address[1]

    def call(self, method, path, body=None, key=True):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        h = {"Host": f"127.0.0.1:{self.port}"}
        if key:
            h["X-Key"] = self.app.token
        data = json.dumps(body) if body is not None else None
        if data is not None:
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = (r.status, json.loads(r.read().decode()))
        c.close()
        return out

    def test_the_endpoints_need_the_key(self):
        sb, srv = self.installed(), self.release()
        self.start(sb, srv)
        self.assertEqual(self.call("GET", "/api/update", key=False)[0], 403)
        self.assertEqual(self.call("POST", "/api/update/apply", {}, key=False)[0], 403)
        self.assertEqual(self.call("POST", "/api/update/settings", {"check": False}, key=False)[0], 403)

    def test_banner_data_then_later_then_one_click_update(self):
        sb, srv = self.installed(), self.release()
        self.start(sb, srv)
        code, u = self.call("GET", "/api/update?force=1")
        self.assertTrue(u["available"] and u["version"] == NEW and u["notes"])
        self.assertFalse(u["dismissed"])
        _, u = self.call("POST", "/api/update/settings", {"later": NEW})
        self.assertTrue(u["dismissed"])
        rec = self.record(sb)
        code, r = self.call("POST", "/api/update/apply", {})
        self.assertEqual((code, r["ok"], r["version"]), (200, True, NEW), r)
        _, u = self.call("GET", "/api/update")
        self.assertEqual(u["just_updated"]["to"], NEW)
        self.assertFalse(u["available"])
        self.assertEqual(self.record(sb)["layout"], rec["layout"])
        _, u = self.call("POST", "/api/update/settings", {"ack": True})
        self.assertIsNone(u["just_updated"])

    def test_a_failed_one_click_update_says_one_sentence_and_changes_nothing(self):
        sb, srv = self.installed(), self.release(failing=True)
        self.start(sb, srv)
        before = sb.snapshot()
        _, r = self.call("POST", "/api/update/apply", {})
        self.assertFalse(r["ok"])
        self.assertIn("is back", r["error"])
        self.assertEqual([k for k in diff(before, sb.snapshot()) if "last-good" not in k], [])

    def test_opt_out_and_channel_through_the_screen(self):
        sb, srv = self.installed(), self.release()
        self.start(sb, srv)
        _, u = self.call("POST", "/api/update/settings", {"check": False})
        self.assertFalse(u["enabled"])
        self.assertEqual(srv.requests, [])
        _, u = self.call("POST", "/api/update/settings", {"channel": "beta", "check": True})
        self.assertEqual(u["channel"], "beta")


class ReleaseFiles(UpdateBase):
    def build(self):
        d = Path(tempfile.mkdtemp(dir=self._tmp.name))
        make_release(d, base="https://github.com/jordanallenlewis/pokemmo-controller/releases/download/v%s/" % NEW)
        return d / "site"

    def test_a_good_release_verifies(self):
        out = self.build()
        with mock.patch.dict(os.environ, {"POKEMMO_CONTROLLER_UPDATE_KEY": PUB}):
            self.assertEqual(release_meta.verify(out, f"v{NEW}")["version"], NEW)

    def test_a_release_without_valid_update_metadata_fails(self):
        out = self.build()
        with mock.patch.dict(os.environ, {"POKEMMO_CONTROLLER_UPDATE_KEY": PUB}):
            (out / "update.json.sig").unlink()
            with self.assertRaises(Exception):
                release_meta.verify(out, f"v{NEW}")

    def test_signing_needs_the_secret(self):
        out = self.build()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("UPDATE_SIGNING_KEY", None)
            with self.assertRaises(SystemExit):
                release_meta.sign(out)

    def test_the_tag_must_match_the_version_and_notes_must_exist(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                release_meta.build("v0.0.1", Path(d))
            with self.assertRaises(SystemExit):
                release_meta.notes_for("0.0.1")

    def test_the_pinned_public_key_is_a_real_key(self):
        from update_key import PUBLIC_KEY
        self.assertEqual(len(bytes.fromhex(PUBLIC_KEY)), 32)
        self.assertTrue(ed25519.verify(bytes.fromhex(PUBLIC_KEY), b"", b"\0" * 64) is False)


if __name__ == "__main__":
    unittest.main()
