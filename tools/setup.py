"""One-step setup: controller binds + (if Steam is installed) the right-stick wheel.

    python tools/setup.py              install, or update an earlier install
    python tools/setup.py --no-wheel   binds only, no Steam involvement
    python tools/setup.py --uninstall  undo everything
    python tools/setup.py --install-ui also keep the remap screen on this computer
    python tools/setup.py --dry-run    show what would change, change nothing
    python tools/setup.py --follow     keep the wheel sized for the game while its resolution changes
    python tools/setup.py --version    print this version

install.ps1 / install.sh run this for you without needing Python installed.
Running it again is safe: it updates what an earlier version wrote and says
"already up to date" when there is nothing to change.
Steam is closed and started again only when its files need to change, and
never while a Steam game is running. PokeMMO must be closed (it rewrites its
settings when it exits).
"""
import argparse, os, signal, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platforms as P  # noqa: E402
import app, apply_native, fit, install_wheel, layout as layout_mod, uninstall  # noqa: E402
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
        app.plan_uninstall(p, pm)
    else:
        apply_native.plan(p, pm, a.name, a.switch_positional, getattr(a, "layout_data", None),
                          getattr(a, "reset_layout", False))
        pick_screen(a, p)
        if steam:
            install_wheel.plan(p, pm, steam)
        app.plan(p, pm, getattr(a, "install_ui", False))
    return p


def pick_screen(a, p):
    """The wheel is sized for the game picture. A size the player gave is kept for good; otherwise
    measure the screen now, so a plain install already fits (a measurement that fails keeps what
    was recorded, or the 4K size)."""
    chosen, reset = getattr(a, "screen", None), getattr(a, "reset_screen", False)
    if chosen or reset:
        layout_mod.set_screen(p.state, chosen, reset, manual=True)
    elif not p.state.get("screen_manual"):
        measured = fit.sanitize(P.game_size())
        if measured:
            layout_mod.set_screen(p.state, measured)


def previous_version(p, pm):
    if p.state.get("version"):
        return p.state["version"]
    if pm and apply_native.installed(pm) and not p.files:  # files: an interrupted first install
        return "an earlier version"
    return None


def describe(p, pm):
    """One line per file a run would write, for --dry-run."""
    for path, data in sorted(p.pending().items(), key=lambda kv: str(kv[0])):
        if data is None:
            what = "remove"
        elif not path.exists():
            what = "create"
        else:
            what = "change"
        print(f"  would {what}: {path}")


def follow(a, limit=None):
    """--follow: keep the wheel sized for the game picture while the resolution changes."""
    pm = P.find_pokemmo(a.pokemmo)
    steam = P.find_steam(a.steam)
    start = Plan(pm)
    if not start.state.get("version"):
        sys.exit("The layout is not installed yet. Run the installer first, then this.")

    def write(size):
        p = Plan(pm)
        layout_mod.set_screen(p.state, size)
        install_wheel.resize_plan(p, steam)
        p.commit()

    print("Watching the game's resolution; the wheel follows it. Press Ctrl+C to stop.\n"
          "Steam reads a layout when the game starts or its controller settings reload: if the wheel "
          "keeps its old size after a change, restart the game from Steam.")
    if hasattr(signal, "SIGTERM"):      # a stop request ends between writes, never half-way through one
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        fit.follow(P.game_size, write, applied=layout_mod.recorded_screen(start.state),
                   interval=a.follow_interval, limit=limit)
    except KeyboardInterrupt:
        print("\nStopped.")


def run(a):
    print(f"PokeMMO controller layout v{VERSION}")
    if not P.WINDOWS and not P.TEST and hasattr(os, "geteuid") and os.geteuid() == 0:
        sys.exit("Run this without sudo: as root it would write the settings of the wrong user.")
    if P.pokemmo_running() and not a.dry_run:
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
    if a.dry_run:
        print("Dry run: nothing will be written, closed or started.")
        if pm:
            print(f"  PokeMMO folder: {pm}")
        if steams:
            print(f"  Steam folder: {steams[0]}")
        if not p.pending():
            print("Nothing would change.")
        else:
            describe(p, pm)
            if any(p.touches(s) for s in steams) and P.steam_running():
                print("  Steam would be closed and started again.")
            print("Run again without --dry-run to do this.")
        return
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
    if p.state.get("app"):
        print(f"Open the remap screen any time with:  {app.how_to_open(pm)}")


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
    ap.add_argument("--dry-run", action="store_true",
                    help="show which files would change and change nothing (PokeMMO may stay open)")
    ap.add_argument("--ui", action="store_true", help="open the remap screen in your browser")
    ap.add_argument("--install-ui", action="store_true",
                    help="also keep the remap screen on this computer, with a launcher (undone by --uninstall)")
    ap.add_argument("--no-browser", action="store_true", help="with --ui: print the address instead of opening it")
    ap.add_argument("--layout", metavar="FILE", help="install your own layout (a file made by remap.py or the remap screen)")
    ap.add_argument("--reset-layout", action="store_true", help="go back to the default layout")
    ap.add_argument("--resolution", metavar="WxH",
                    help="the size of the game picture, like 1920x1080: the wheel is sized to fit it "
                         "(remembered; run again after you change the game's resolution)")
    ap.add_argument("--reset-resolution", dest="reset_screen", action="store_true",
                    help="go back to the 4K wheel size")
    ap.add_argument("--follow", action="store_true",
                    help="keep running and re-size the wheel whenever the game's resolution changes")
    ap.add_argument("--follow-interval", type=float, default=1.0, metavar="SECONDS", help=argparse.SUPPRESS)
    ap.add_argument("--version", action="version", version=f"pokemmo-controller {VERSION}")
    a = ap.parse_args()
    if a.layout:
        try:
            a.layout_data = layout_mod.loads(Path(a.layout).expanduser().read_bytes())
        except OSError as e:
            sys.exit(f"Could not read {a.layout}: {e.strerror or e}. Nothing was changed.")
        except layout_mod.LayoutError as e:
            sys.exit(f"{a.layout} was not used: {e}\nNothing was changed.")
    a.screen = None
    if a.resolution:
        try:
            a.screen = layout_mod.parse_resolution(a.resolution)
        except layout_mod.LayoutError as e:
            sys.exit(f"{e}\nNothing was changed.")
    if a.follow:
        if a.uninstall or a.layout or a.install_ui or a.resolution or a.reset_screen:
            sys.exit("--follow runs on its own: use it without the other options.")
        follow(a, limit=int(os.environ["POKEMMO_CONTROLLER_TEST_POLLS"]) if P.TEST and os.environ.get("POKEMMO_CONTROLLER_TEST_POLLS") else None)
        return
    if a.ui:
        import ui
        ui.serve(a.pokemmo, a.steam, a.no_wheel, not a.no_browser)
        return
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
