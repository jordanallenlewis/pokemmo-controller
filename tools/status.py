"""What is installed and whether it still matches: one answer for the remap screen and the
command line (pmc). Read-only: it never writes a file.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_native  # noqa: E402
import install_wheel  # noqa: E402
import layout as L  # noqa: E402
import platforms as P  # noqa: E402
from common import NEWER, STATE_NAME, VERSION, Plan, newer_record  # noqa: E402


def record(pokemmo):
    """The install record (config/pokemmo-controller.json) as a dict; {} when there is none."""
    try:
        rec = json.loads((Path(pokemmo) / "config" / STATE_NAME).read_text(encoding="utf-8"))
        return rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        return {}


def drift(found, steam=None, no_wheel=False):
    """(binds_current, steam_current): would the installer, run now, change nothing? That is
    the whole truth about the files, whatever the record says (the game rewrites its
    settings, Steam drops a layout). False when nothing is installed or the check fails."""
    pm = Path(found)
    if not record(found):
        return False, False
    try:
        p = Plan(pm)
        apply_native.plan(p, pm)
        binds = not p.pending()
        current = False
        if not no_wheel:
            try:
                root = P.find_steam(steam)
            except SystemExit:
                root = None
            if root:
                p2 = Plan(pm)
                install_wheel.plan(p2, pm, root)
                current = not p2.pending()
        return binds, current
    except Exception:  # noqa: BLE001  a check that cannot run must not show a green tick
        return False, False


def find(pokemmo=None):
    """(PokeMMO folder or None, the reason it was not found)."""
    try:
        return str(P.find_pokemmo(pokemmo)), None
    except SystemExit as e:
        return None, str(e).splitlines()[0]


def summary(found, steam=None, no_wheel=False):
    """What the app keeps true, from the install record (not a probe of the game)."""
    rec = record(found) if found else {}
    files = [str(k) for k in (rec.get("files") or {})]
    screen = L.recorded_screen(rec) if rec else None
    binds_ok, steam_ok = drift(found, steam, no_wheel) if found else (False, False)
    return {
        "pokemmo": bool(found),
        "pokemmo_open": P.pokemmo_running(),
        "installed": bool(rec),
        "installed_version": rec.get("version") if rec else None,
        "binds": any(f.endswith("main.properties") for f in files),
        "steam": any(f.endswith(".vdf") for f in files),
        "binds_current": binds_ok,
        "steam_current": steam_ok,
        "wheel_screen": list(screen) if screen else None,
        "custom": bool(rec.get("layout")),
        "newer": newer_record(rec),     # a newer version made the install: this copy only reads it
        "version": VERSION,
    }


def _check(cid, ok, detail, fix=""):
    return {"id": cid, "ok": bool(ok), "detail": detail, "fix": "" if ok else fix}


def doctor(found, steam=None, no_wheel=False, reason=None):
    """Every check with what it found and, when it fails, the one command that fixes it.
    Returns (summary, checks). A failed check is a problem; notes (ok) are only information."""
    if not found:
        return summary(None), [_check("pokemmo", False, reason or "PokeMMO's settings were not found.",
                                      "Start PokeMMO once, close it, then run this again, or pass --pokemmo <folder>.")]
    s = summary(found, steam, no_wheel)
    checks = [_check("pokemmo", True, f"PokeMMO folder: {found}")]
    if not s["installed"]:
        checks.append(_check("installed", False, "The layout is not installed.", "Run: pmc install"))
        return s, checks
    checks.append(_check("installed", True, f"Installed (v{s['installed_version'] or '?'})."))
    if s["newer"]:
        # every other check would point at `pmc install`, which refuses this install
        checks.append(_check("newer", False, f"{NEWER} This copy (v{VERSION}) does not change it.",
                             "Use the newer version that made the install."))
        if s["pokemmo_open"]:
            checks.append(_check("pokemmo_open", True, "PokeMMO is open: close it before you change anything."))
        return s, checks
    if s["installed_version"] != VERSION:
        checks.append(_check("version", False, f"Installed v{s['installed_version']}, this is v{VERSION}.",
                             "Run: pmc install"))
    else:
        checks.append(_check("version", True, f"The installed version is this one (v{VERSION})."))
    if s["binds"]:
        checks.append(_check("binds", s["binds_current"],
                             "The controller binds are in place." if s["binds_current"] else
                             "PokeMMO's settings changed since the install (the game rewrites them) "
                             "and no longer match the layout.", "Close PokeMMO, then run: pmc install"))
    if s["steam"]:
        checks.append(_check("wheel", s["steam_current"],
                             "The Steam wheel is in place." if s["steam_current"] else
                             "Steam's wheel files differ from the layout (Steam can drop them, or Steam was not found).",
                             "Close PokeMMO, then run: pmc install"))
    else:
        try:
            have = P.find_steam(steam)
        except SystemExit:
            have = None
        if have and not no_wheel:
            checks.append(_check("wheel", True, "The Steam wheel is not installed (binds only)."))
    if s["pokemmo_open"]:
        checks.append(_check("pokemmo_open", True, "PokeMMO is open: close it before you change anything."))
    return s, checks
