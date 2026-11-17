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

FOLLOW_SH = """#!/bin/sh
# Started at login: keeps the PokeMMO wheel sized for the game. Quits quietly if there is no Python 3.9+.
here=$(cd "$(dirname "$0")" && pwd)
for py in python3 python; do
    if [ "$(uname -s)" = Darwin ] && [ "$(command -v $py)" = /usr/bin/$py ] && ! xcode-select -p >/dev/null 2>&1; then
        continue  # macOS stub that pops an install dialog
    fi
    if command -v "$py" >/dev/null 2>&1 &&
        "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        exec "$py" "$here/tools/setup.py" --follow --background "$@"
    fi
done
exit 0
"""

FOLLOW_CMD = ("""@echo off
rem Started at login: keeps the PokeMMO wheel sized for the game. Quits quietly if there is no Python 3.9+.
set "HERE=%~dp0"
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if not errorlevel 1 ( py -3 "%HERE%tools\\setup.py" --follow --background %* & goto :eof )
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if not errorlevel 1 ( python "%HERE%tools\\setup.py" --follow --background %* & goto :eof )
exit /b 0
""").replace("\n", "\r\n")

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


def follow_launcher(pm: Path) -> Path:
    import platforms as P
    return app_dir(pm) / ("follow.cmd" if P.WINDOWS else "follow.sh")


def plan(p, pm: Path, install_ui=False, follow=False):
    """Add the app files to the plan: for the remap screen (asked for, or installed by an earlier
    run) and for the follower that starts at login. The tools copy is the same for both."""
    ui = install_ui or bool(p.state.get("app"))
    if not (ui or follow):
        return
    root, here = app_dir(pm), Path(__file__).resolve().parent
    files = {root / "tools" / f.name: f.read_bytes()
             for f in sorted(here.iterdir()) if f.suffix in (".py", ".html")}
    files[root / "remap.sh"] = LAUNCHER_SH.encode("utf-8")
    files[root / "remap.cmd"] = LAUNCHER_CMD.encode("utf-8")
    files[root / "follow.sh"] = FOLLOW_SH.encode("utf-8")
    files[root / "follow.cmd"] = FOLLOW_CMD.encode("utf-8")
    for path, data in files.items():
        p.put(path, data, backup_ok=False)
    for key in list(p.files):  # a file an older version put there that this one does not
        if _is_app_file(pm, key) and Path(key) not in files:
            p.delete(key)
    if ui:
        p.state["app"] = True


def plan_follow(p, pm: Path, want: bool):
    """The login entry that starts the follower (setup.py --follow --background), or its removal.
    Returns False when it was wanted but this computer has no Python 3.9+ to start it with."""
    import platforms as P
    old = [Path(x) for x in p.state.get("autostart", [])]
    if not want:
        for path in old:
            p.delete(path)
        p.state.pop("autostart", None)
        return True
    if not P.python_for_login():
        for path in old:
            p.delete(path)
        p.state.pop("autostart", None)
        return False
    entries = P.login_entries(follow_launcher(pm))
    for path, data in entries.items():
        p.put(path, data, backup_ok=False)
    for path in old:
        if path not in entries:
            p.delete(path)
    p.state["autostart"] = [str(x) for x in entries]
    return True


def plan_uninstall(p, pm):
    for key in p.state.get("autostart", []):
        p.delete(key)
    p.state.pop("autostart", None)
    p.state.pop("follow", None)
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
