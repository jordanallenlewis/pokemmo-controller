"""Keep a copy of the remap screen on disk, so it opens with one short command.

python tools/setup.py --install-ui   install (or update), and keep the screen in
                                     <PokeMMO folder>/pokemmo-controller/

The copy is the same standard-library Python this install ran from (nothing is
downloaded), plus two small launchers: remap.cmd (Windows) and remap.sh (macOS,
Linux, Steam Deck). Every file goes through the install record, so uninstall
removes it, and a file you add to that folder yourself is left alone. Without the
flag nothing is added.
"""
from pathlib import Path

APP_DIR = "pokemmo-controller"
RAW = "https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/"
ONE_LINER = {
    "sh": "curl -fsSL " + RAW + "install.sh" + " | sh -s -- --ui",
    "ps1": "& ([scriptblock]::Create((irm " + RAW + "install.ps1))) -Ui",
}

LAUNCHER_SH = """#!/bin/sh
# Opens the PokeMMO controller remap screen in your browser.
here=$(cd "$(dirname "$0")" && pwd)
for py in python3 python; do
    if [ "$(uname -s)" = Darwin ] && [ "$(command -v $py)" = /usr/bin/$py ] && ! xcode-select -p >/dev/null 2>&1; then
        continue  # macOS stub that pops an install dialog
    fi
    if command -v "$py" >/dev/null 2>&1 &&
        "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        exec "$py" "$here/tools/setup.py" --ui "$@"
    fi
done
echo "Python 3.9 or newer was not found. Open the screen with the one-command installer instead:" >&2
echo "  %(sh)s" >&2
exit 1
""" % ONE_LINER

LAUNCHER_CMD = ("""@echo off
rem Opens the PokeMMO controller remap screen in your browser.
set "HERE=%~dp0"
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if not errorlevel 1 ( py -3 "%HERE%tools\\setup.py" --ui %* & goto :eof )
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if not errorlevel 1 ( python "%HERE%tools\\setup.py" --ui %* & goto :eof )
echo Python 3.9 or newer was not found. Open the screen with the one-command installer instead.
echo In PowerShell, run the command from the README section "Change what a button does".
exit /b 1
""").replace("\n", "\r\n")


def app_dir(pm: Path) -> Path:
    return Path(pm) / APP_DIR


def _is_app_file(pm, key):
    return app_dir(pm) in Path(key).parents


def plan(p, pm: Path, install_ui=False):
    """Add the app files to the plan (when asked for, or when an earlier run installed it)."""
    if not (install_ui or p.state.get("app")):
        return
    root, here = app_dir(pm), Path(__file__).resolve().parent
    files = {root / "tools" / f.name: f.read_bytes()
             for f in sorted(here.iterdir()) if f.suffix in (".py", ".html")}
    files[root / "remap.sh"] = LAUNCHER_SH.encode("utf-8")
    files[root / "remap.cmd"] = LAUNCHER_CMD.encode("utf-8")
    for path, data in files.items():
        p.put(path, data, backup_ok=False)
    for key in list(p.files):  # a file an older version put there that this one does not
        if _is_app_file(pm, key) and Path(key) not in files:
            p.delete(key)
    p.state["app"] = True


def plan_uninstall(p, pm):
    if pm is None:
        return
    for key in list(p.files):
        if _is_app_file(pm, key):
            p.delete(key)
    p.state.pop("app", None)


def how_to_open(pm: Path) -> str:
    import platforms as P
    launcher = app_dir(pm) / ("remap.cmd" if P.WINDOWS else "remap.sh")
    return f'"{launcher}"' if P.WINDOWS else f'sh "{launcher}"'
