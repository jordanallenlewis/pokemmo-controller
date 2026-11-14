"""One-step setup: controller binds + (if Steam is installed) the right-stick wheel.

    python tools/setup.py              install everything
    python tools/setup.py --no-wheel   binds only, no Steam involvement
    python tools/setup.py --uninstall  undo everything

install.ps1 / install.sh run this for you without needing Python installed.
If Steam is open, it is closed gracefully first and started again afterwards.
PokeMMO must be closed (it rewrites its settings when it exits).
"""
import argparse, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platforms as P  # noqa: E402


def run_tool(script, args):
    r = subprocess.run([sys.executable, str(Path(__file__).with_name(script)), *args])
    if r.returncode:
        sys.exit(r.returncode)


def steam_cmd(steam: Path):
    if P.WINDOWS:
        return [str(steam / "steam.exe")]
    if P.MAC:
        return ["open", "-a", "Steam", "--args"]
    if ".var/app/com.valvesoftware.Steam" in str(steam):
        return ["flatpak", "run", "com.valvesoftware.Steam"]
    return ["steam"]


def stop_steam(steam: Path):
    print("Closing Steam (it rewrites its settings when it exits)...")
    try:
        subprocess.Popen(steam_cmd(steam) + ["-shutdown"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
    for _ in range(60):
        time.sleep(1)
        if not P.steam_running():
            time.sleep(2)  # let it finish writing files
            return
    sys.exit("Steam did not close. Exit it from its menu (Steam > Exit) and run this again.")


def start_steam(steam: Path):
    try:
        subprocess.Popen(steam_cmd(steam), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        print("Started Steam again.")
    except OSError:
        print("Start Steam again yourself.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-wheel", action="store_true", help="skip the Steam right-stick wheel")
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--steam", help="Steam folder")
    ap.add_argument("--switch-positional", action="store_true",
                    help="Nintendo pads: confirm on the bottom button like Xbox")
    a = ap.parse_args()

    if P.pokemmo_running():
        sys.exit("PokeMMO is open. Close it (it rewrites its settings on exit), then run this again.")
    pm = ["--pokemmo", a.pokemmo] if a.pokemmo else []
    steam = None
    if not a.no_wheel:
        try:
            steam = P.find_steam(a.steam)
        except SystemExit:
            print("Steam not found: installing the controller binds without the wheel.")
    restart = bool(steam) and P.steam_running()
    if restart:
        stop_steam(steam)
    st = ["--steam", str(steam)] if steam else []

    if a.uninstall:
        run_tool("uninstall.py", pm + st)
    else:
        run_tool("apply_native.py", pm + (["--switch-positional"] if a.switch_positional else []))
        if steam:
            run_tool("install_wheel.py", pm + st)
    if restart:
        start_steam(steam)
    if not a.uninstall:
        print("\nAll set." + (" Launch PokeMMO from your Steam library to get the wheel." if steam
                              else " Start PokeMMO and play."))


if __name__ == "__main__":
    main()
