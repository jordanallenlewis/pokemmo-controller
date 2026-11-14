"""The one-line installers, run the way users run them, on a local copy of the repo.

  Windows:      Get-Content install.ps1 | iex   (same as irm ... | iex)
  macOS/Linux:  sh < install.sh                 (same as curl ... | sh), under every shell found

POKEMMO_CONTROLLER_SRC points them at an archive built from this checkout.
Set POKEMMO_CONTROLLER_NETWORK_TESTS=1 to also test the "no Python" path, which
downloads uv and a private Python from GitHub.
"""
import os, shutil, subprocess, sys, tarfile, unittest, zipfile
from pathlib import Path
from urllib.parse import quote

from helpers import ROOT, Sandbox
import common

NETWORK = os.environ.get("POKEMMO_CONTROLLER_NETWORK_TESTS") == "1"
FILES = ["install.ps1", "install.sh", "LICENSE"] + [
    p.relative_to(ROOT).as_posix() for d in ("tools", "steam") for p in (ROOT / d).glob("*") if p.is_file()
    and not p.name.endswith(".pyc")]


def build_archive(dest: Path, kind):
    top = "pokemmo-controller-main/"
    if kind == "zip":
        out = dest / "src.zip"
        with zipfile.ZipFile(out, "w") as z:
            for f in FILES:
                z.write(ROOT / f, top + f)
    else:
        out = dest / "src.tar.gz"
        with tarfile.open(out, "w:gz") as t:
            for f in FILES:
                t.add(str(ROOT / f), top + f)
    return out


class InstallerBase(unittest.TestCase):
    kind = None

    def setUp(self):
        self.sb = Sandbox(name="Installer Täst")
        self.addCleanup(self.sb.cleanup)
        self.tmp = self.sb.root / "temp"
        self.tmp.mkdir()
        self.src = build_archive(self.sb.root.parent, self.kind)

    def env(self, **extra):
        e = dict(POKEMMO_CONTROLLER_SRC=str(self.src), POKEMMO_CONTROLLER_POKEMMO_DIR=str(self.sb.pokemmo),
                 POKEMMO_CONTROLLER_STEAM_DIR=str(self.sb.steam),
                 TEMP=str(self.tmp), TMP=str(self.tmp), TMPDIR=str(self.tmp))
        e.update(extra)
        return self.sb.env(**e)

    def snapshot(self):
        """Every file except the temp folder and PowerShell's own startup cache."""
        return {k: v for k, v in self.sb.snapshot().items()
                if not k.startswith("temp/") and "/Microsoft/" not in k
                and not (v is None and k.startswith("home/"))}  # empty folders in the fake home

    def check_round_trip(self, run):
        before = self.snapshot()
        r = run(False)
        self.assertIn(f"Installed v{common.VERSION}", r.stdout + r.stderr)
        self.assertIn("KEY_RING_FOCUS", self.sb.props.read_text(encoding="utf-8"))
        installed = self.snapshot()
        r = run(False)
        self.assertIn("Already up to date", r.stdout)
        self.assertEqual(installed, self.snapshot())
        r = run(True)
        self.assertIn("Removed", r.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(list(self.tmp.iterdir()), [], "installer left files in the temp folder")


@unittest.skipUnless(sys.platform == "win32", "Windows PowerShell")
class PowerShell(InstallerBase):
    kind = "zip"

    def ps(self, exe, uninstall, policy="Restricted", **env):
        script = str(Path(ROOT / "install.ps1"))
        body = (f"[scriptblock]::Create((Get-Content -Raw -LiteralPath '{script}'))"
                if uninstall else None)
        cmd = (f"& ({body}) -Uninstall" if uninstall
               else f"Get-Content -Raw -LiteralPath '{script}' | iex")
        # afterwards: the user's session must be as it was
        cmd += "; Write-Output \"EAP=$ErrorActionPreference LOC=$([uri]::EscapeDataString((Get-Location).Path))\""
        r = subprocess.run([exe, "-NoProfile", "-ExecutionPolicy", policy, "-Command", cmd],
                           env=self.env(**env), capture_output=True, text=True, cwd=str(self.sb.root.resolve()),
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"EAP=Continue LOC={quote(str(self.sb.root.resolve()), safe='')}", r.stdout)
        self.assertNotIn("Exception", r.stderr)
        return r

    def round_trip(self, exe, **env):
        if not shutil.which(exe):
            self.skipTest(f"{exe} not installed")
        self.check_round_trip(lambda u: self.ps(exe, u, **env))

    def test_windows_powershell_5(self):
        self.round_trip("powershell")

    def test_powershell_7(self):
        self.round_trip("pwsh")

    @unittest.skipUnless(NETWORK, "set POKEMMO_CONTROLLER_NETWORK_TESTS=1")
    def test_without_python_uses_private_copy(self):
        self.round_trip("powershell", POKEMMO_CONTROLLER_FORCE_UV="1")

    def test_failure_is_reported_and_cleaned_up(self):
        self.sb.props.unlink()
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Get-Content -Raw -LiteralPath '{ROOT / 'install.ps1'}' | iex"],
                           env=self.env(), capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("main.properties", r.stdout + r.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_no_network(self):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Get-Content -Raw -LiteralPath '{ROOT / 'install.ps1'}' | iex"],
                           env=self.env(POKEMMO_CONTROLLER_SRC="https://127.0.0.1:9/nothing.zip"),
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Check your internet connection", r.stdout + r.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])


@unittest.skipIf(sys.platform == "win32", "POSIX shells")
class PosixShell(InstallerBase):
    kind = "tar"

    def sh(self, shell, uninstall, **env):
        args = [shell, "-s", "--", "--uninstall"] if uninstall else [shell]
        if shell == "zsh":
            args[1:1] = ["--emulate", "sh"]
        if shell == "busybox":
            args[1:1] = ["sh"]
        r = subprocess.run(args, input=(ROOT / "install.sh").read_bytes(), env=self.env(**env),
                           capture_output=True)
        r.stdout, r.stderr = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def round_trip(self, shell, **env):
        if not shutil.which(shell):
            self.skipTest(f"{shell} not installed")
        self.check_round_trip(lambda u: self.sh(shell, u, **env))

    def test_sh(self):
        self.round_trip("sh")

    def test_dash(self):
        self.round_trip("dash")

    def test_bash(self):
        self.round_trip("bash")

    def test_bash_posix_mode(self):  # what macOS /bin/sh is
        if not shutil.which("bash"):
            self.skipTest("bash not installed")
        self.check_round_trip(lambda u: self.sh_posix(u))

    def sh_posix(self, uninstall):
        args = ["bash", "--posix", "-s"] + (["--", "--uninstall"] if uninstall else [])
        r = subprocess.run(args, input=(ROOT / "install.sh").read_bytes(), env=self.env(), capture_output=True)
        r.stdout, r.stderr = r.stdout.decode(), r.stderr.decode()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_zsh(self):
        self.round_trip("zsh")

    def test_busybox_ash(self):
        self.round_trip("busybox")

    @unittest.skipUnless(NETWORK, "set POKEMMO_CONTROLLER_NETWORK_TESTS=1")
    def test_without_python_uses_private_copy(self):
        self.round_trip("sh", POKEMMO_CONTROLLER_FORCE_UV="1")

    def test_no_network(self):
        r = subprocess.run(["sh"], input=(ROOT / "install.sh").read_bytes(), capture_output=True,
                           env=self.env(POKEMMO_CONTROLLER_SRC="https://127.0.0.1:9/nothing.tar.gz"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(b"Check your internet connection", r.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
