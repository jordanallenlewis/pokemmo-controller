"""Updates: find a newer signed release, and install it with one step.

How it stays safe
  * Each release ships update.json (version, notes, download address, SHA-256) and
    update.json.sig, an Ed25519 signature over the exact bytes of update.json. The public
    key is pinned in tools/update_key.py. No valid signature, no update: nothing is
    downloaded into place, nothing is run.
  * The download must match the signed SHA-256 and size, and must be a newer version.
  * Before anything changes, the version that is running is copied to
    <PokeMMO folder>/pokemmo-controller/last-good and the install record is copied aside.
    If the new version's setup fails, that copy is run again (it puts the old binds, wheel
    and app files back) and the player's own layout is checked to be unchanged.
  * Per user, no admin. The check sends only the request for two public files (no ids,
    no version, no counters). It can be turned off, and installs managed by winget or
    Homebrew are told to update with that tool instead.

Standard library only.
"""
import base64, hashlib, json, os, re, shutil, subprocess, sys, tarfile, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ed25519, platforms as P  # noqa: E402
from common import VERSION, Plan, write_atomic  # noqa: E402
from update_key import PUBLIC_KEY  # noqa: E402

REPO = "jordanallenlewis/pokemmo-controller"
MANIFEST = "update.json"
SIGNATURE = "update.json.sig"
ASSET_PREFIX = f"https://github.com/{REPO}/releases/download/"
STABLE_URL = f"https://github.com/{REPO}/releases/latest/download/"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=15"
MAX_MANIFEST = 64 * 1024
MAX_ASSET = 60 * 1024 * 1024
CHANNELS = ("stable", "beta")
CHECK_EVERY = 20 * 3600     # "about daily": the app asks again after this long
LAST_GOOD = "last-good"
WORK = "update-work"


class UpdateError(Exception):
    """A problem with a plain sentence for the player."""


# ------------------------------------------------------------------ versions
def parse_version(v):
    """'1.3.0-beta.2' -> a tuple that sorts right (a pre-release sorts before its release)."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?", str(v).strip())
    if not m:
        raise UpdateError(f"Unreadable version: {v!r}.")
    pre = m.group(4)
    ids = tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in pre.split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 1 if not pre else 0, ids)


def is_newer(candidate, current=VERSION):
    return parse_version(candidate) > parse_version(current)


# ------------------------------------------------------------------ settings (kept in the install record)
def settings(state):
    s = state.get("update") if isinstance(state.get("update"), dict) else {}
    channel = s.get("channel") if s.get("channel") in CHANNELS else "stable"
    return {"check": s.get("check", True) is not False, "channel": channel,
            "last_check": s.get("last_check") if isinstance(s.get("last_check"), (int, float)) else 0,
            "available": s.get("available") if isinstance(s.get("available"), str) else None,
            "just_updated": s.get("just_updated") if isinstance(s.get("just_updated"), dict) else None,
            "later": s.get("later") if isinstance(s.get("later"), str) else None}


def save_settings(pm, **changes):
    """Write the update settings into the install record (only when something is installed)."""
    p = Plan(pm)
    if not p.state.get("version"):
        return False
    cur = dict(p.state.get("update") or {})
    for k, v in changes.items():
        if v is None:
            cur.pop(k, None)
        else:
            cur[k] = v
    p.state["update"] = cur
    write_atomic(p.state_path, json.dumps(p.state, indent=2, sort_keys=True).encode() + b"\n")
    return True


def managed_by(here=None, env=None):
    """'winget' or 'homebrew' when a package manager owns this copy, else None."""
    env = os.environ if env is None else env
    if env.get("POKEMMO_CONTROLLER_MANAGED") in ("winget", "homebrew"):
        return env["POKEMMO_CONTROLLER_MANAGED"]
    s = str(Path(here or __file__).resolve()).replace("\\", "/").lower()
    if "/microsoft/winget/" in s or "/winget/packages/" in s:
        return "winget"
    if "/cellar/pokemmo-controller" in s or "/homebrew/" in s:
        return "homebrew"
    return None


def manager_hint(which):
    return {"winget": "This copy was installed with winget. Update it with:  winget upgrade pokemmo-controller",
            "homebrew": "This copy was installed with Homebrew. Update it with:  brew upgrade pokemmo-controller"}[which]


# ------------------------------------------------------------------ network
def _key():
    if P.TEST and os.environ.get("POKEMMO_CONTROLLER_UPDATE_KEY"):
        return bytes.fromhex(os.environ["POKEMMO_CONTROLLER_UPDATE_KEY"])
    return bytes.fromhex(PUBLIC_KEY)


def _base():
    if P.TEST and os.environ.get("POKEMMO_CONTROLLER_UPDATE_BASE"):
        return os.environ["POKEMMO_CONTROLLER_UPDATE_BASE"].rstrip("/") + "/"
    return None


def _allowed_asset(url):
    if url.startswith(ASSET_PREFIX):
        return True
    return P.TEST and bool(_base()) and url.startswith(_base())


def _get(url, limit):
    """GET a public file. Only the request itself is sent: no cookies, no ids."""
    req = urllib.request.Request(url, headers={"User-Agent": "pokemmo-controller-update-check"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read(limit + 1)
    except Exception as e:  # urllib raises many kinds; the player needs one sentence
        raise UpdateError("Could not reach the update server. Check your internet connection; "
                          "nothing was changed.") from e
    if len(data) > limit:
        raise UpdateError("The update server sent something too large; nothing was changed.")
    return data


def verify_manifest(raw, sig_b64):
    """The manifest as a dict, only if the signature is valid for exactly these bytes."""
    try:
        sig = base64.b64decode(sig_b64.strip(), validate=True)
    except Exception:
        sig = b""
    if not ed25519.verify(_key(), raw, sig):
        raise UpdateError("The update's signature did not check out, so it was not used. "
                          "Nothing was changed.")
    try:
        m = json.loads(raw)
    except ValueError as e:
        raise UpdateError("The update information is unreadable. Nothing was changed.") from e
    need = ("version", "url", "sha256", "size", "notes", "channel")
    if not isinstance(m, dict) or m.get("schema") != 1 or any(k not in m for k in need):
        raise UpdateError("The update information is incomplete. Nothing was changed.")
    parse_version(m["version"])
    if not (isinstance(m["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", m["sha256"])):
        raise UpdateError("The update information is incomplete. Nothing was changed.")
    if not (isinstance(m["size"], int) and 0 < m["size"] <= MAX_ASSET) or not isinstance(m["notes"], list):
        raise UpdateError("The update information is incomplete. Nothing was changed.")
    if m["channel"] not in CHANNELS or not isinstance(m["url"], str) or not _allowed_asset(m["url"]):
        raise UpdateError("The update points somewhere unexpected, so it was not used. Nothing was changed.")
    return m


def _beta_base():
    """The newest release of any kind (pre-releases included) that carries update metadata."""
    for rel in json.loads(_get(RELEASES_API, MAX_MANIFEST * 16)):
        names = {a.get("name"): a.get("browser_download_url") for a in rel.get("assets", [])}
        if MANIFEST in names and SIGNATURE in names and not rel.get("draft"):
            return names[MANIFEST].rsplit("/", 1)[0] + "/"
    raise UpdateError("No release with update information was found.")


def fetch_manifest(channel="stable"):
    base = _base() or (_beta_base() if channel == "beta" else STABLE_URL)
    raw = _get(base + MANIFEST, MAX_MANIFEST)
    return verify_manifest(raw, _get(base + SIGNATURE, MAX_MANIFEST).decode("ascii", "replace"))


def check(channel="stable", current=VERSION):
    """{'available': bool, 'version', 'notes', 'channel', 'manifest'} for the newest signed release.
    A stable player is never offered a pre-release; a manifest that is not newer is not an update."""
    m = fetch_manifest(channel)
    if channel == "stable" and "-" in m["version"]:
        return {"available": False, "version": current}
    if not is_newer(m["version"], current):
        return {"available": False, "version": current}
    return {"available": True, "version": m["version"], "notes": [str(n) for n in m["notes"]][:3],
            "channel": m["channel"], "manifest": m}


def download(m, work):
    """The release archive in <work>, checked against the signed size and SHA-256."""
    data = _get(m["url"], m["size"])
    if len(data) != m["size"] or hashlib.sha256(data).hexdigest() != m["sha256"]:
        raise UpdateError("The download did not match its signed checksum, so it was not used. "
                          "Nothing was changed.")
    out = Path(work) / "release.tar.gz"
    out.write_bytes(data)
    return out


def extract(archive, dest):
    """Unpack a release archive; refuses anything that would land outside <dest> or is not a plain file."""
    dest = Path(dest).resolve()
    with tarfile.open(archive) as t:
        for member in t.getmembers():
            target = (dest / member.name).resolve()
            if dest not in target.parents and target != dest:
                raise UpdateError("The download held an unsafe path, so it was not used. Nothing was changed.")
            if not (member.isfile() or member.isdir()):
                raise UpdateError("The download held an unexpected file type, so it was not used. "
                                  "Nothing was changed.")
        try:
            t.extractall(dest, filter="data")   # members were checked above; no links or devices exist
        except TypeError:                       # Python without extraction filters
            t.extractall(dest)
    found = sorted(dest.glob("*/tools/setup.py")) or sorted(dest.glob("tools/setup.py"))
    if not found:
        raise UpdateError("The download was incomplete, so it was not used. Nothing was changed.")
    return found[0].parent.parent


def tools_version(root):
    m = re.search(r'^VERSION = "([^"]+)"', (Path(root) / "tools" / "common.py").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


# ------------------------------------------------------------------ apply with rollback
def app_root(pm):
    return Path(pm) / "pokemmo-controller"


def _run_setup(root, pm, extra, env=None):
    cmd = [sys.executable, str(Path(root) / "tools" / "setup.py"), "--pokemmo", str(pm)] + list(extra)
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env)


def _copy_tools(src_root, dst):
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "tools").mkdir(parents=True)
    for f in (Path(src_root) / "tools").iterdir():
        if f.is_file() and f.suffix in (".py", ".html", ".json", ".css", ".md"):
            shutil.copy2(f, dst / "tools" / f.name)
    steam = Path(src_root) / "steam"
    if steam.is_dir():
        shutil.copytree(steam, dst / "steam", dirs_exist_ok=True)


def apply(pm, m, steam=None, say=print, env=None):
    """Install the verified release described by manifest m. Returns the new version.
    On any failure the version that was running comes back, and UpdateError says what happened."""
    pm = Path(pm)
    if P.pokemmo_running():
        raise UpdateError("PokeMMO is open. Close it, then press Update again: it rewrites its settings "
                          "when it closes, and the update must not race that.")
    game = P.steam_game_running()
    if game:
        raise UpdateError("A Steam game is running. Close it, then update: Steam has to restart for the wheel.")
    plan = Plan(pm)
    if not plan.state.get("version"):
        raise UpdateError("The layout is not installed yet. Run the installer first.")
    before_record = (plan.state_path.read_bytes() if plan.state_path.exists() else b"")
    work = app_root(pm) / WORK
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        say(f"Downloading v{m['version']}...")
        root = extract(download(m, work), work / "new")
        if tools_version(root) != m["version"]:
            raise UpdateError("The download is not the version it says it is, so it was not used. "
                              "Nothing was changed.")
        say("Checked: signature, size and checksum match.")
        # keep the running version for rollback (the last known-good)
        here = Path(__file__).resolve().parent.parent
        good = app_root(pm) / LAST_GOOD
        _copy_tools(here, good)
        extra = (["--steam", str(steam)] if steam else []) + (["--install-ui"] if plan.state.get("app") else [])
        say("Updating...")
        r = _run_setup(root, pm, extra, env)
        ok = r.returncode == 0 and Plan(pm).state.get("version") == m["version"]
        if not ok:
            say("The update failed; putting the previous version back...")
            back = _run_setup(good, pm, extra, env)
            _restore_layout(pm, before_record)
            same = back.returncode == 0
            raise UpdateError(
                ("The update did not work, so v%s is back exactly as it was and your layout is untouched."
                 if same else "The update did not work and putting v%s back needs another try: run the "
                              "installer again. Your layout is untouched.") % VERSION)
        save_settings(pm, just_updated={"from": VERSION, "to": m["version"], "at": int(time.time())},
                      available=None)
        return m["version"]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _restore_layout(pm, before_record):
    """After a rollback the player's own layout (and update settings) must be what they were."""
    try:
        old = json.loads(before_record) if before_record else {}
    except ValueError:
        return
    p = Plan(pm)
    changed = False
    for key in ("layout", "update", "screen", "screen_manual", "switch_positional", "follow"):
        if key in old and p.state.get(key) != old[key]:
            p.state[key] = old[key]
            changed = True
    if changed:
        write_atomic(p.state_path, json.dumps(p.state, indent=2, sort_keys=True).encode() + b"\n")


def cleanup(pm):
    """Uninstall: drop the kept last-good copy and any work folder."""
    for name in (LAST_GOOD, WORK):
        shutil.rmtree(app_root(pm) / name, ignore_errors=True)
    try:
        app_root(pm).rmdir()
    except OSError:
        pass


# ------------------------------------------------------------------ the app's cached check
def status(pm, force=False, clock=time.time):
    """What the app shows: respects the opt-out, asks again only about daily, never raises."""
    st = Plan(pm).state if pm else {}
    s = settings(st)
    out = {"enabled": s["check"], "channel": s["channel"], "current": VERSION,
           "managed": managed_by(), "available": False, "just_updated": s["just_updated"], "dismissed": False}
    if out["managed"]:
        out["managed_hint"] = manager_hint(out["managed"])
    if not s["check"] or not st.get("version"):
        return out
    if not force and clock() - s["last_check"] < CHECK_EVERY:
        if s["available"] and is_newer(s["available"]):
            out.update(available=True, version=s["available"], notes=list(st.get("update", {}).get("notes", [])),
                       dismissed=s["later"] == s["available"])
        return out
    try:
        c = check(s["channel"])
    except (UpdateError, ValueError, OSError):
        out["error"] = "Could not check for updates just now."
        return out
    notes = c.get("notes", [])
    save_settings(pm, last_check=int(clock()), available=c["version"] if c["available"] else None,
                  notes=notes if c["available"] else None)
    if c["available"]:
        out.update(available=True, version=c["version"], notes=notes, dismissed=s["later"] == c["version"])
    return out
