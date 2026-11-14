"""One-step setup: controller binds + (if Steam is installed) the right-stick wheel.

    python tools/setup.py              install, or update an earlier install
    python tools/setup.py --no-wheel   binds only, no Steam involvement
    python tools/setup.py --uninstall  undo everything
    python tools/setup.py --version    print this version

install.ps1 / install.sh run this for you without needing Python installed.
Running it again is safe: it updates what an earlier version wrote and says
"already up to date" when there is nothing to change.
Steam is closed and started again only when its files need to change, and
never while a Steam game is running. PokeMMO must be closed (it rewrites its
settings when it exits).
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platforms as P  # noqa: E402
import apply_native, install_wheel, uninstall  # noqa: E402
from common import VERSION, Plan  # noqa: E402

for _s in (sys.stdout, sys.stderr):  # paths with any characters print on any console
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def steam_cmd(steam: Path):
    if P.WINDOWS:
        return [str(steam / "steam.exe")]
    if P.MAC:
        return ["open", "-a", "Steam", "--args"]
    if ".var/app/com.valvesoftware.Steam" in str(steam):
        return ["flatpak", "run", "com.valvesoftware.Steam"]
    return ["steam"]


def stop_steam(steam: Path):
    game = P.steam_game_running()
    if game:
        sys.exit(f"A Steam game is running (app {game}). Close it, then run this again:\n"
                 "the installer has to restart Steam and that would close your game.")
    print("Closing Steam (it rewrites its settings when it exits)...")
    try:
        if P.MAC:  # `open --args -shutdown` does not reach a Steam that is already running
            cmd = ["osascript", "-e", 'quit app "Steam"']
        else:
            cmd = steam_cmd(steam) + ["-shutdown"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
    for _ in range(60):
        time.sleep(1)
        if not P.steam_running():
            time.sleep(2)  # let it finish writing files
            return
    sys.exit("Steam did not close. Exit it from its menu (Steam > Exit) and run this again.\n"
             "Nothing was changed.")


def start_steam(steam: Path):
    try:
        subprocess.Popen(steam_cmd(steam), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        print("Started Steam again.")
    except OSError:
        print("Start Steam again yourself.")


def build_plan(a, pm, steam, steams):
    p = Plan(pm)
    if a.uninstall:
        uninstall.plan(p, pm, steams)
    else:
        apply_native.plan(p, pm, a.name, a.switch_positional)
        if steam:
            install_wheel.plan(p, pm, steam)
    return p


def previous_version(p, pm):
    if p.state.get("version"):
        return p.state["version"]
    if pm and apply_native.installed(pm) and not p.files:  # files: an interrupted first install
        return "an earlier version"
    return None


def run(a):
    print(f"PokeMMO controller layout v{VERSION}")
    if not P.WINDOWS and not P.TEST and hasattr(os, "geteuid") and os.geteuid() == 0:
        sys.exit("Run this without sudo: as root it would write the settings of the wrong user.")
    if P.pokemmo_running():
        sys.exit("PokeMMO is open. Close it (it rewrites its settings on exit), then run this again.")
    try:
        pm = P.find_pokemmo(a.pokemmo)
    except SystemExit:
        if not a.uninstall:
            raise
        pm = None
        print("PokeMMO not found: cleaning up Steam only.")
    steam, steams = None, []
    if a.uninstall:
        steams = uninstall.steam_roots(Plan(pm), a.steam)
    elif not a.no_wheel:
        try:
            steam = P.find_steam(a.steam)
            steams = [steam]
        except SystemExit:
            print("Steam not found: installing the controller binds without the wheel.")

    p = build_plan(a, pm, steam, steams)
    prev = previous_version(p, pm)
    if not p.pending():
        if a.uninstall:
            print("Nothing to undo: the layout is not installed.")
            if pm and p.state:
                p.commit(uninstall=True)  # drop the leftover record and backups
        else:
            if prev != VERSION and pm:
                p.save_state()
            if prev and prev != VERSION:
                print(f"Updated from {prev if prev.startswith('an ') else 'v' + prev} to v{VERSION}: "
                      "your settings already matched this version.")
            else:
                print(f"Already up to date (v{VERSION}). Nothing changed.")
        return

    restart = False
    if any(p.touches(s) for s in steams) and P.steam_running():
        stop_steam(steam or steams[0])
        restart = True
        p = build_plan(a, pm, steam, steams)  # Steam may have rewritten its files on exit
    try:
        p.commit(uninstall=a.uninstall)
        if a.uninstall:
            uninstall.remove_empty_dirs(steams, p.state.get("created_dirs", []))
    finally:
        if restart:
            start_steam(steam or steams[0])

    for n in p.notes:
        print(" ", n)
    if a.uninstall:
        print("\nRemoved. PokeMMO and Steam are back to how they were before the install.")
        return
    if prev is None:
        print(f"\nInstalled v{VERSION}.", end="")
    elif prev == VERSION:
        print(f"\nv{VERSION} was already installed; refreshed the settings above.", end="")
    else:
        print(f"\nUpdated from {prev if prev.startswith('an ') else 'v' + prev} to v{VERSION}.", end="")
    print(" Launch PokeMMO from your Steam library to get the wheel." if steam
          else " Start PokeMMO and play.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uninstall", action="store_true", help="undo everything")
    ap.add_argument("--no-wheel", action="store_true", help="skip the Steam right-stick wheel")
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--steam", help="Steam folder")
    ap.add_argument("--name", action="append", default=[],
                    help="extra controller name to bind (as PokeMMO shows it); repeatable")
    ap.add_argument("--switch-positional", action="store_true", default=None,
                    help="Nintendo pads: confirm on the bottom button like Xbox (remembered)")
    ap.add_argument("--switch-labels", dest="switch_positional", action="store_false",
                    help="Nintendo pads: confirm on the printed A (the default)")
    ap.add_argument("--version", action="version", version=f"pokemmo-controller {VERSION}")
    a = ap.parse_args()
    try:
        run(a)
    except KeyboardInterrupt:
        sys.exit("\nStopped. Every file is either fully updated or untouched; "
                 "run the command again to finish, or with --uninstall to undo.")
    except OSError as e:
        sys.exit(f"Could not change {e.filename or 'a file'}: {e.strerror or e}.\n"
                 "Close PokeMMO and Steam, check you can write to that folder, then run this again.")


if __name__ == "__main__":
    main()
