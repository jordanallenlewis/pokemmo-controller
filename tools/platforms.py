"""Find PokeMMO and Steam on Windows, macOS and Linux, and check if they run.

Data-folder rules come from PokeMMO's own launcher
(github.com/PokeMMO/pokemmo-launcher, Launcher.java):
  - Windows, Linux .zip/.sh: the install folder itself
  - macOS app: ~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live
  - Flatpak:   ~/.var/app/com.pokemmo.PokeMMO/data/pokemmo-client-live
  - Snap:      ~/snap/pokemmo/common/pokemmo-client-live

Overrides: --pokemmo / --steam, or the environment variables
POKEMMO_CONTROLLER_POKEMMO_DIR / POKEMMO_CONTROLLER_STEAM_DIR.
POKEMMO_CONTROLLER_TEST=1 is for sandbox tests: it never looks at system-wide
folders or the registry, and treats PokeMMO and Steam as closed.
"""
import os, re, subprocess, sys
from pathlib import Path

HOME = Path.home()
WINDOWS, MAC = sys.platform == "win32", sys.platform == "darwin"
LINUX = not WINDOWS and not MAC
TEST = os.environ.get("POKEMMO_CONTROLLER_TEST") == "1"


def _env_path(var, *rest):
    v = os.environ.get(var)
    return Path(v, *rest) if v else None


def _sandboxed(paths):
    """In test mode keep only folders inside the (fake) home or app-data folders."""
    if not TEST:
        return paths
    roots = [HOME] + [Path(os.environ[v]) for v in ("LOCALAPPDATA", "APPDATA", "XDG_DATA_HOME")
                      if os.environ.get(v)]
    return [p for p in paths if any(r == p or r in p.parents for r in roots)]


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
    return _sandboxed([p for p in c if p])


def find_pokemmo(override=None):
    """Return the PokeMMO data folder (the one holding config/main.properties)."""
    override = override or os.environ.get("POKEMMO_CONTROLLER_POKEMMO_DIR")
    if override:
        p = Path(override).expanduser()
        if (p / "config" / "main.properties").is_file():
            return p
        sys.exit(f"No config/main.properties in {p}. Start PokeMMO once, close it, try again.")
    for p in pokemmo_candidates():
        if (p / "config" / "main.properties").is_file():
            return p
    tried = "\n  ".join(str(p) for p in pokemmo_candidates())
    sys.exit("Could not find PokeMMO's config/main.properties. Is PokeMMO installed? Start it once,\n"
             f"close it, and run this again, or pass --pokemmo <folder>. Looked in:\n  {tried}")


def steam_candidates():
    if WINDOWS:
        c = []
        try:
            if TEST:
                raise OSError
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
    env = os.environ.get("POKEMMO_CONTROLLER_STEAM_DIR")
    return ([Path(env).expanduser()] if env else []) + _sandboxed(c)


def find_steam(override=None):
    override = override or os.environ.get("POKEMMO_CONTROLLER_STEAM_DIR")
    if override:
        p = Path(override).expanduser()
        if not (p / "userdata").is_dir():
            sys.exit(f"No userdata folder in {p}: that is not a Steam folder.")
        return p.resolve()
    for p in steam_candidates():
        if (p / "userdata").is_dir():
            return p.resolve()
    tried = "\n  ".join(str(p) for p in steam_candidates())
    sys.exit(f"Could not find Steam (needed for the wheel). Pass --steam <folder>. Looked in:\n  {tried}")


def _running(names):
    if TEST:  # sandbox tests on fake folders
        return False
    if WINDOWS:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                             errors="replace").stdout.lower()
        return any(f'"{n.lower()}.exe"' in out for n in names)
    out = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True,
                         errors="replace").stdout
    procs = {Path(l.strip()).name.lower() for l in out.splitlines() if l.strip()}
    return any(n.lower() in procs for n in names)


def pokemmo_running():
    return _running(["PokeMMO"])


def steam_running():
    return _running(["steam", "steam_osx"])


def steam_game_running():
    """App id of the game Steam says is running (0 = none). Closing Steam would close it."""
    if TEST:
        return 0
    if WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                return int(winreg.QueryValueEx(k, "RunningAppID")[0])
        except (OSError, ValueError):
            return 0
    for reg in (HOME / ".steam/registry.vdf", HOME / "Library/Application Support/Steam/registry.vdf",
                HOME / ".var/app/com.valvesoftware.Steam/.steam/registry.vdf"):
        try:
            m = re.search(r'"RunningAppID"\s+"(\d+)"', reg.read_text(encoding="utf-8", errors="replace"))
            if m and int(m.group(1)):
                return int(m.group(1))
        except OSError:
            pass
    return 0


def require_closed(steam=False):
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
