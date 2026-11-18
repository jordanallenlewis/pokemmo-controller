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
import os, re, shutil, subprocess, sys, tempfile
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


def _other_drive_folders():
    """PokeMMO unpacked straight on another Windows drive (D:\\PokeMMO, D:\\Games\\PokeMMO)."""
    if TEST:
        return []
    out = []
    for letter in "DEFGH":
        root = Path(letter + ":\\")
        try:
            if not root.exists():
                continue
        except OSError:
            continue
        out += [root / "PokeMMO", root / "Games" / "PokeMMO"]
    return out


def pokemmo_candidates():
    if WINDOWS:
        c = [Path(r"C:\Program Files\PokeMMO"), Path(r"C:\Program Files (x86)\PokeMMO"),
             _env_path("LOCALAPPDATA", "PokeMMO"), _env_path("LOCALAPPDATA", "Programs", "PokeMMO"),
             _env_path("APPDATA", "PokeMMO"), HOME / "PokeMMO", HOME / "Desktop" / "PokeMMO",
             HOME / "Games" / "PokeMMO"]
        c += _other_drive_folders()
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


def steam_library_folders(steam_root):
    """Library folders Steam lists in steamapps/libraryfolders.vdf (the Steam folder itself first)."""
    libs = [Path(steam_root)]
    try:
        text = (Path(steam_root) / "steamapps" / "libraryfolders.vdf").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', text):
        p = Path(m.group(1).replace("\\\\", "\\"))
        if p not in libs:
            libs.append(p)
    return libs


def steam_pokemmo_candidates():
    """PokeMMO installed through Steam: <library>/steamapps/common/PokeMMO."""
    out = []
    for root in steam_candidates():
        if not root.is_dir():
            continue
        for lib in steam_library_folders(root):
            out.append(lib / "steamapps" / "common" / "PokeMMO")
    return _sandboxed(out) if TEST else out


def find_pokemmo(override=None):
    """Return the PokeMMO data folder (the one holding config/main.properties)."""
    override = override or os.environ.get("POKEMMO_CONTROLLER_POKEMMO_DIR")
    if override:
        p = Path(override).expanduser()
        if (p / "config" / "main.properties").is_file():
            return p
        sys.exit(f"No config/main.properties in {p}. Start PokeMMO once, close it, try again.")
    every = pokemmo_candidates() + [p for p in steam_pokemmo_candidates() if p not in pokemmo_candidates()]
    for p in every:
        if (p / "config" / "main.properties").is_file():
            return p
    tried = "\n  ".join(str(p) for p in every)
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


# ------------------------------------------------------- the size of the game picture
def parse_xwininfo(text):
    """(w, h) from `xwininfo` output, or None."""
    w, h = re.search(r"^\s*Width:\s*(\d+)", text, re.M), re.search(r"^\s*Height:\s*(\d+)", text, re.M)
    return (int(w.group(1)), int(h.group(1))) if w and h else None


def parse_xrandr(text):
    """(w, h) of the primary (else first) connected screen in `xrandr --current` output, or None."""
    best = None
    for line in text.splitlines():
        m = re.match(r"^\S+ connected( primary)? (\d+)x(\d+)\+-?\d+\+-?\d+", line)
        if m:
            size = (int(m.group(2)), int(m.group(3)))
            if m.group(1):
                return size
            best = best or size
    return best


def parse_system_profiler(text):
    """(w, h) in real pixels of the main display from `system_profiler SPDisplaysDataType -json`."""
    import json
    try:
        data = json.loads(text)
    except ValueError:
        return None
    shots = []
    gpus = data.get("SPDisplaysDataType", []) if isinstance(data, dict) else []
    for gpu in gpus if isinstance(gpus, list) else []:
        displays = gpu.get("spdisplays_ndrvs", []) if isinstance(gpu, dict) else []
        for d in displays if isinstance(displays, list) else []:
            if not isinstance(d, dict):
                continue
            m = re.search(r"(\d+)\s*x\s*(\d+)", str(d.get("_spdisplays_pixels", "")))
            if m:
                size = (int(m.group(1)), int(m.group(2)))
                if d.get("spdisplays_main") == "spdisplays_yes":
                    return size
                shots.append(size)
    return shots[0] if shots else None


def _run_text(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


PAD_WORDS = re.compile(r"controller|gamepad|joystick|dualshock|dualsense|x-?box|pro pad|8bitdo|joy-?con|steam deck", re.I)
NOT_PADS = re.compile(r"mouse|keyboard|trackpad|receiver|touch|headset|audio|webcam|camera|bluetooth radio|consumer control", re.I)


def _pad_name(name):
    name = name.strip().strip('"').strip()
    return name if name and len(name) <= 80 and PAD_WORDS.search(name) and not NOT_PADS.search(name) else None


def _unique(names):
    return list(dict.fromkeys(n for n in map(_pad_name, names) if n))


def parse_proc_input(text):
    """Pad names from /proc/bus/input/devices: the entries that have a js handler."""
    out = []
    for block in text.split("\n\n"):
        name = re.search(r'^N: Name="(.*)"$', block, re.M)
        handlers = re.search(r"^H: Handlers=(.*)$", block, re.M)
        if name and handlers and re.search(r"\bjs\d+\b", handlers.group(1)):
            out.append(name.group(1))
    return _unique(out)


def parse_pad_lines(text):
    """One device name per line (what the Windows query prints)."""
    return _unique(text.splitlines())


def parse_ioreg(text):
    """Pad names from `ioreg -r -c IOHIDDevice -l` ("Product" = "...") on macOS."""
    return _unique(re.findall(r'"Product"\s*=\s*"([^"]*)"', text))


def connected_pad_names():
    """Names of the pads plugged in or paired right now, best effort; [] when unknown.
    Sandbox tests get only what POKEMMO_CONTROLLER_TEST_PADS (names split by ;) says."""
    try:
        if TEST:
            return _unique(os.environ.get("POKEMMO_CONTROLLER_TEST_PADS", "").split(";"))
        if WINDOWS:
            return parse_pad_lines(_run_text([
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-PnpDevice -PresentOnly -Class HIDClass,XboxComposite,Bluetooth,USB "
                "-ErrorAction SilentlyContinue | ForEach-Object { $_.FriendlyName }"]))
        if MAC:
            return parse_ioreg(_run_text(["ioreg", "-r", "-c", "IOHIDDevice", "-l"]))
        try:
            return parse_proc_input(Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return []
    except Exception:  # detection is a convenience: never stop an install
        return []


GAME_EXE = re.compile(r"^pokemmo[\w .-]*\.exe$", re.I)
GAME_TITLE = re.compile(r"^pokemmo( -.*)?$", re.I)


def pick_game_window(windows):
    """windows: (title, exe name, width, height, minimized) of every visible window.
    -> ("size", (w, h)) for the game window, ("minimized", None) when only a minimized one is
    there, or (None, None) when there is no game window. The game is the window of the
    PokeMMO program; where the program is unknown, a title that is exactly "PokeMMO" counts.
    A browser tab or folder called "PokeMMO Forums" does not: its size is not the game's.
    With several game windows (a launcher, the client) the largest picture wins."""
    shown, hidden = [], False
    for title, exe, w, h, minimized in windows:
        ours = bool(GAME_EXE.match(exe or "")) or (not exe and bool(GAME_TITLE.match(title or "")))
        if not ours:
            continue
        if minimized:
            hidden = True
        else:
            shown.append((w, h))
    if shown:
        return "size", max(shown, key=lambda s: s[0] * s[1])
    return ("minimized", None) if hidden else (None, None)


def _windows_game_size():
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    try:  # real pixels, not the scaled ones a DPI setting would report
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (OSError, AttributeError):
        try:
            u.SetProcessDPIAware()
        except AttributeError:
            pass
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    seen = []

    def exe_of(hwnd):
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = k.OpenProcess(0x1000, False, pid.value)       # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return buf.value.replace("/", "\\").rsplit("\\", 1)[-1]
            return ""
        finally:
            k.CloseHandle(h)

    def each(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, buf, 256)
        if not buf.value.lower().startswith("pokemmo") and "pokemmo" not in exe_of(hwnd).lower():
            return True
        r = wintypes.RECT()
        u.GetClientRect(hwnd, ctypes.byref(r))
        seen.append((buf.value, exe_of(hwnd), r.right - r.left, r.bottom - r.top, bool(u.IsIconic(hwnd))))
        return True

    u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(each), 0)
    kind, size = pick_game_window(seen)
    if kind == "size":
        return size
    if kind == "minimized":
        return None     # minimized: no picture to read now, the caller keeps the last good size
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)   # no game window: the main screen


def game_size():
    """(w, h) in pixels of the picture the game draws (its window, else the main screen), or
    None when it cannot be told right now. Any value may be 0 or odd mid-switch: the caller
    (fit.py) filters. Never raises."""
    forced = os.environ.get("POKEMMO_CONTROLLER_TEST_SIZE_FILE")
    if TEST and not forced:
        return None         # sandbox tests never read the real display of the machine they run on
    if TEST:                # sandbox tests: the "screen" is a file holding WxH
        try:
            m = re.search(r"(-?\d+)\s*x\s*(-?\d+)", Path(forced).read_text())
            return (int(m.group(1)), int(m.group(2))) if m else None
        except OSError:
            return None
    try:
        if WINDOWS:
            return _windows_game_size()
        if MAC:
            return parse_system_profiler(_run_text(["system_profiler", "SPDisplaysDataType", "-json"]))
        return (parse_xwininfo(_run_text(["xwininfo", "-name", "PokeMMO"]))
                or parse_xrandr(_run_text(["xrandr", "--current"])))
    except Exception:  # noqa: BLE001  a display query must never stop the follower
        return None


# ------------------------------------------------ the follower at login, and one copy only
def python_for_login():
    """True when this computer has a Python 3.9+ the login entry can start. The installers may
    have used a private copy that is gone after the run: then nothing could start at login."""
    probe = "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
    for name in (("py", "python") if WINDOWS else ("python3", "python")):
        exe = shutil.which(name)
        if not exe:
            continue
        if MAC and exe == "/usr/bin/" + name and not _run_text(["xcode-select", "-p"]).strip():
            continue  # the stub that pops an install dialog
        cmd = [exe, "-3", "-c", probe] if name == "py" else [exe, "-c", probe]
        try:
            if subprocess.run(cmd, capture_output=True, timeout=20).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def _xml(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def login_entries(follow_launcher: Path):
    """{path: bytes}: the files that start follow_launcher when this user logs in.
    Windows: a script in the user's Startup folder. macOS: a LaunchAgent. Linux and Steam Deck
    Desktop Mode: an XDG autostart entry. Nothing needs admin rights; each file is one entry."""
    launcher = str(follow_launcher)
    if WINDOWS:
        base = _env_path("APPDATA") or HOME / "AppData" / "Roaming"
        text = ('Set sh = CreateObject("WScript.Shell")\r\n'
                'sh.Run Chr(34) & "' + launcher.replace('"', '') + '" & Chr(34), 0, False\r\n')
        return {base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                / "pokemmo-controller-follow.vbs": b"\xff\xfe" + text.encode("utf-16-le")}
    if MAC:
        text = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n'
                '  <key>Label</key><string>com.pokemmo-controller.follow</string>\n'
                '  <key>ProgramArguments</key><array><string>/bin/sh</string><string>'
                + _xml(launcher) + '</string></array>\n'
                '  <key>RunAtLoad</key><true/>\n</dict>\n</plist>\n')
        return {HOME / "Library" / "LaunchAgents" / "com.pokemmo-controller.follow.plist": text.encode("utf-8")}
    quoted = launcher.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    quoted = quoted.replace("%", "%%")
    text = ("[Desktop Entry]\nType=Application\nName=PokeMMO controller wheel\n"
            "Comment=Keeps the controller wheel sized for the game\n"
            f'Exec=sh "{quoted}"\nTerminal=false\nX-GNOME-Autostart-enabled=true\n')
    base = _env_path("XDG_CONFIG_HOME") or HOME / ".config"
    return {base / "autostart" / "pokemmo-controller-follow.desktop": text.encode("utf-8")}


_LOCKS = []


def single_instance(key):
    """True for the first process to ask with this key, False while another still holds it.
    The lock goes when the process ends, however it ends."""
    import hashlib
    path = Path(tempfile.gettempdir()) / ("pokemmo-controller-follow-"
                                          + hashlib.sha1(str(key).encode("utf-8", "replace")).hexdigest()[:12] + ".lock")
    try:
        f = open(path, "a+b")
    except OSError:
        return True    # cannot lock: better two followers than none
    try:
        if WINDOWS:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    _LOCKS.append(f)
    return True


def start_detached(cmd):
    """Start cmd on its own, unattached from this console, so it outlives the installer."""
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if WINDOWS:
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000   # detached, new group, no window
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kw)
        return True
    except OSError:
        return False

# --- the app window --------------------------------------------------------------------------
# The remap screen is a page served on 127.0.0.1. To feel like an app it opens in a browser's
# "app mode" (its own window, no address bar, no tabs). Edge ships with Windows, so on the common
# system there is nothing to install; where none is found the caller opens a normal browser tab.

def _app_browser_names(windows=WINDOWS, mac=MAC):
    """Browser programs that can open an app-mode window, best first."""
    if windows:
        roots = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        roots = [r for r in roots if r] or [r"C:\Program Files (x86)", r"C:\Program Files"]
        rel = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
               r"BraveSoftware\Brave-Browser\Application\brave.exe"]
        return [str(Path(r, x)) for x in rel for r in roots]
    if mac:
        apps = ["Microsoft Edge", "Google Chrome", "Brave Browser", "Chromium"]
        out = []
        for base in ("/Applications", str(HOME / "Applications")):
            out += [f"{base}/{a}.app/Contents/MacOS/{a}" for a in apps]
        return out
    return ["microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable",
            "chromium", "chromium-browser", "brave-browser", "brave"]


def _on_path(name):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d, name)
        if d and p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def app_browser_candidates():
    """Browsers found on this machine. Sandbox tests never look at the real machine."""
    if TEST:
        return []
    found = []
    for n in _app_browser_names():
        p = n if os.sep in n or "/" in n else _on_path(n)
        if p and Path(p).is_file() and p not in found:
            found.append(p)
    return found


def find_app_browser(override=None):
    """The browser to use, or None. override / POKEMMO_CONTROLLER_BROWSER must exist."""
    forced = override or os.environ.get("POKEMMO_CONTROLLER_BROWSER")
    if forced:
        return forced if Path(forced).is_file() else None
    found = app_browser_candidates()
    return found[0] if found else None


def app_window_command(browser, url, profile):
    """Command line for an app-mode window on `url`. Only the local remap address is accepted."""
    if not re.match(r"^http://127\.0\.0\.1:\d+/", url):
        raise ValueError("the app window only opens the local remap screen")
    return [browser, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1120,780",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions"]


def open_app_window(url, override=None, profile=None, start=None):
    """Open the remap screen in its own window. Returns the process, or None when no suitable
    browser is found or it will not start (the caller then opens a normal tab)."""
    browser = find_app_browser(override)
    if not browser:
        return None
    if profile is None:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(HOME / ".local" / "share")
        profile = str(Path(base, "pokemmo-controller", "app-window"))
    Path(profile).mkdir(parents=True, exist_ok=True)
    cmd = app_window_command(browser, url, profile)
    try:
        return (start or (lambda c: subprocess.Popen(c, stdout=subprocess.DEVNULL,
                                                     stderr=subprocess.DEVNULL)))(cmd)
    except OSError:
        return None
