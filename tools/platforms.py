"""Find PokeMMO and Steam on Windows, macOS and Linux, and check if they run.

Data-folder rules come from PokeMMO's own launcher
(github.com/PokeMMO/pokemmo-launcher, Launcher.java):
  - Windows, Linux .zip/.sh: the install folder itself
  - macOS app: ~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live
  - Flatpak:   ~/.var/app/com.pokemmo.PokeMMO/data/pokemmo-client-live
  - Snap:      ~/snap/pokemmo/common/pokemmo-client-live
"""
import os, subprocess, sys
from pathlib import Path

HOME = Path.home()
WINDOWS, MAC = sys.platform == "win32", sys.platform == "darwin"
LINUX = not WINDOWS and not MAC


def _env_path(var, *rest):
    v = os.environ.get(var)
    return Path(v, *rest) if v else None


def pokemmo_candidates():
    if WINDOWS:
        c = [Path(r"C:\Program Files\PokeMMO"), Path(r"C:\Program Files (x86)\PokeMMO"),
             _env_path("LOCALAPPDATA", "PokeMMO"), _env_path("LOCALAPPDATA", "Programs", "PokeMMO"),
             _env_path("APPDATA", "PokeMMO"), HOME / "PokeMMO", HOME / "Desktop" / "PokeMMO",
             HOME / "Games" / "PokeMMO"]
    elif MAC:
        c = [HOME / "Library/Application Support/com.pokeemu.macos/pokemmo-client-live",
             Path("/Applications/PokeMMO.app/Contents/Resources/pokemmo-client-live")]
    else:
        c = [HOME / ".var/app/com.pokemmo.PokeMMO/data/pokemmo-client-live",
             HOME / "snap/pokemmo/common/pokemmo-client-live",
             _env_path("XDG_DATA_HOME", "pokemmo-client-live"),
             HOME / ".local/share/pokemmo-client-live", HOME / "PokeMMO", HOME / "pokemmo",
             HOME / "Games" / "PokeMMO", HOME / ".local/share/PokeMMO", Path("/opt/PokeMMO")]
    return [p for p in c if p]


def find_pokemmo(override=None):
    """Return the PokeMMO data folder (the one holding config/main.properties)."""
    if override:
        p = Path(override).expanduser()
        if (p / "config" / "main.properties").exists():
            return p
        sys.exit(f"No config/main.properties in {p}. Start PokeMMO once, close it, try again.")
    for p in pokemmo_candidates():
        if (p / "config" / "main.properties").exists():
            return p
    tried = "\n  ".join(str(p) for p in pokemmo_candidates())
    sys.exit("Could not find PokeMMO's config/main.properties. Start PokeMMO once, close it,\n"
             f"or pass --pokemmo <folder>. Looked in:\n  {tried}")


def steam_candidates():
    if WINDOWS:
        c = []
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                c.append(Path(winreg.QueryValueEx(k, "SteamPath")[0]))
        except OSError:
            pass
        c += [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    elif MAC:
        c = [HOME / "Library/Application Support/Steam"]
    else:
        c = [HOME / ".steam/steam", HOME / ".local/share/Steam",
             HOME / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
             HOME / "snap/steam/common/.local/share/Steam"]
    return c


def find_steam(override=None):
    if override:
        return Path(override).expanduser()
    for p in steam_candidates():
        if (p / "userdata").is_dir():
            return p.resolve()
    tried = "\n  ".join(str(p) for p in steam_candidates())
    sys.exit(f"Could not find Steam (needed for the wheel). Pass --steam <folder>. Looked in:\n  {tried}")


def _running(names):
    if WINDOWS:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return any(f"{n.lower()}.exe" in out for n in names)
    out = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True).stdout
    procs = {Path(l.strip()).name.lower() for l in out.splitlines() if l.strip()}
    return any(n.lower() in procs for n in names)


def pokemmo_running():
    return _running(["PokeMMO"])


def steam_running():
    return _running(["steam", "steam_osx"])


def require_closed(steam=False):
    if os.environ.get("POKEMMO_CONTROLLER_TEST") == "1":  # sandbox tests on fake folders
        return
    busy = (["PokeMMO"] if pokemmo_running() else []) + (["Steam"] if steam and steam_running() else [])
    if busy:
        sys.exit(f"Close {' and '.join(busy)} first: it rewrites these files when it exits.")


def shortcut_target(pokemmo_dir: Path):
    """(exe, start_dir, launch_options) for a Steam non-Steam-game shortcut."""
    if WINDOWS:
        exe = pokemmo_dir / "PokeMMO.exe"
        return f'"{exe}"', f'"{pokemmo_dir}\\"', ""
    if MAC:
        app = Path("/Applications/PokeMMO.app")
        if not app.exists():
            app = HOME / "Applications/PokeMMO.app"
        return f'"{app}"', f'"{app.parent}/"', ""
    if ".var/app/com.pokemmo.PokeMMO" in str(pokemmo_dir):
        return '"/usr/bin/flatpak"', '"/usr/bin/"', "run com.pokemmo.PokeMMO"
    if "snap/pokemmo" in str(pokemmo_dir):
        return '"/snap/bin/pokemmo"', '"/snap/bin/"', ""
    return f'"{pokemmo_dir / "PokeMMO.sh"}"', f'"{pokemmo_dir}/"', ""
