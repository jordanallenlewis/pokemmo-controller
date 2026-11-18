"""Shared pieces: the version, safe file writes, Java .properties editing, and
the install record that makes reinstalling, updating and uninstalling exact.

Every write is atomic (temp file + rename), so Ctrl-C or a crash never leaves a
half-written file, and keeps the file's own line endings. The first time a file
is changed, its original is kept as <file>.bak-pokemmo-controller. The record
(config/pokemmo-controller.json next to PokeMMO's main.properties) holds the
installed version and a hash of every file written, so uninstall can put back
the original bytes when nothing else changed the file since.
"""
import glob, hashlib, json, os, re, shutil, tempfile, time
from pathlib import Path

VERSION = "1.3.0-beta.1"
SUFFIX = ".bak-pokemmo-controller"
STATE_NAME = "pokemmo-controller.json"
MAP_KEY = "client.controls.controller_input_maps_gdx_2"
NATIVE_KEY = "client.input.controllers.enable_native_support"


# ---------------------------------------------------------------- bytes / text
def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(p):
    try:
        return Path(p).read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        return None


def decode(data: bytes):
    """bytes -> (text with \\n line ends, the file's newline). Never fails."""
    nl = "\r\n" if b"\r\n" in data else "\n"
    return data.decode("utf-8", "surrogateescape").replace("\r\n", "\n"), nl


def encode(text: str, nl: str = "\n") -> bytes:
    return text.replace("\n", nl).encode("utf-8", "surrogateescape")


def backup_path(p) -> Path:
    p = Path(p)
    return p.with_name(p.name + SUFFIX)


def _umask():
    if os.name == "nt":
        return 0
    m = os.umask(0)
    os.umask(m)
    return m


def sweep_tmp(path, min_age=0):
    """Delete leftovers of write_atomic next to path (name.XXXX.tmp) that a killed process left
    behind. On Windows a process that is stopped while it waits for a busy file cannot clean up.
    min_age: only those older than this many seconds (another run may be writing one right now)."""
    path = Path(path)
    try:
        for f in path.parent.glob(glob.escape(path.name) + ".*.tmp"):
            try:
                if min_age and time.time() - f.stat().st_mtime < min_age:
                    continue
                f.unlink()
            except OSError:
                pass
    except OSError:
        pass


def write_atomic(path, data: bytes):
    """Replace path with data in one step: readers see the old or the new file, never half."""
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        raise SystemExit(f"{path} is read-only. Make it writable, then run this again. Nothing was changed in it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    sweep_tmp(path, min_age=60)
    try:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    except PermissionError:
        if not path.exists():
            raise
        with open(path, "r+b") as f:  # folder not writable but the file is
            f.write(data)
            f.truncate()
        return
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            shutil.copymode(path, tmp)
        else:
            os.chmod(tmp, 0o666 & ~_umask())
        for attempt in range(10):  # antivirus / indexers can hold a file for a moment on Windows
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.3)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def remove(p):
    try:
        Path(p).unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- .properties
def split_lines(text):
    lines = text.split("\n")
    final = lines[-1] == ""
    if final:
        lines.pop()
    return lines, final


def join_lines(lines, final):
    s = "\n".join(lines)
    return s + "\n" if final and lines else s


_KEY = re.compile(r"[ \t\f]*((?:\\.|[^\s=:\\])+)[ \t\f]*[=:]?[ \t\f]*")


def line_key(line):
    s = line.lstrip(" \t\f")
    if not s or s[0] in "#!":
        return None
    m = _KEY.match(line)
    return m.group(1) if m else None


def line_value(line):
    return line[_KEY.match(line).end():]


def get_prop(lines, key):
    val = None
    for line in lines:
        if line_key(line) == key:
            val = line_value(line)  # Java: the last one wins
    return val


def set_props(lines, want):
    """want: {key: raw value, or None to delete}. Keeps every other line as is."""
    out, seen = [], set()
    for line in lines:
        k = line_key(line)
        if k in want:
            seen.add(k)
            if want[k] is None:
                continue
            line = f"{k}={want[k]}"
        out.append(line)
    out += [f"{k}={v}" for k, v in want.items() if v is not None and k not in seen]
    return out


def unescape(v):
    """java.util.Properties escapes -> text."""
    def rep(m):
        s = m.group(1)
        if s[0] == "u":
            return chr(int(s[1:], 16))
        return {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}.get(s, s)
    return re.sub(r"\\(u[0-9a-fA-F]{4}|.)", rep, v)


def escape(v):
    """text -> java.util.Properties value (what PokeMMO itself writes)."""
    out = []
    for i, ch in enumerate(v):
        if ch == " " and i == 0:
            out.append("\\ ")
        elif ch in "\\#!=:":
            out.append("\\" + ch)
        elif ch in "\t\n\r\f":
            out.append({"\t": "\\t", "\n": "\\n", "\r": "\\r", "\f": "\\f"}[ch])
        elif ord(ch) < 0x20 or ord(ch) > 0x7E:
            out.append("".join(f"\\u{c:04X}" for c in _utf16(ch)))
        else:
            out.append(ch)
    return "".join(out)


def _utf16(ch):
    b = ch.encode("utf-16-be", "surrogatepass")
    return [int.from_bytes(b[i:i + 2], "big") for i in range(0, len(b), 2)]


# ---------------------------------------------------------------- the plan
class Plan:
    """Collects every file change first, then writes them all.

    Nothing touches the disk until commit(), so a bad file found halfway
    (corrupt, read-only, unreadable) stops the run before anything changed.
    """

    def __init__(self, pokemmo=None):
        self.pokemmo = Path(pokemmo) if pokemmo else None
        self.state = self._load_state()
        self.files = self.state.setdefault("files", {})
        self.changes = {}        # Path -> bytes, or None to delete
        self.backup_ok = {}      # Path -> False when the file already holds our changes
        self.notes = []          # lines to print after commit
        self.drop_backups = []   # uninstall: backups to delete at the end
        self.fresh = False       # nothing installed: backups left by an old uninstall are stale

    # state record
    @property
    def state_path(self):
        return self.pokemmo / "config" / STATE_NAME if self.pokemmo else None

    def _load_state(self):
        try:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
            return st if isinstance(st, dict) else {}
        except (AttributeError, OSError, ValueError):
            return {}

    # reading what a file will look like
    def current(self, p):
        p = Path(p)
        return self.changes[p] if p in self.changes else read_bytes(p)

    def put(self, p, data: bytes, backup_ok=True):
        p = Path(p)
        self.changes[p] = data
        self.backup_ok[p] = backup_ok and self.backup_ok.get(p, True)

    def delete(self, p):
        self.changes[Path(p)] = None

    def pending(self):
        return {p: d for p, d in self.changes.items() if read_bytes(p) != d}

    def touches(self, root):
        root = Path(root).resolve()
        return any(root == p.resolve() or root in p.resolve().parents for p in self.pending())

    def exact_original(self, p):
        """Original bytes (None = file did not exist) if only we changed p since its
        backup; False when someone else changed it too and a merge is needed."""
        rec = self.files.get(str(Path(p)))
        cur = read_bytes(p)
        if not rec or not rec.get("pristine") or cur is None or sha(cur) != rec.get("sha"):
            return False
        if rec.get("created"):
            return None
        bak = read_bytes(backup_path(p))
        return bak if bak is not None else False

    # writing
    def commit(self, uninstall=False):
        pending = self.pending()
        for p in pending:  # check every file first so a read-only one stops the run before any write
            if p.exists() and not os.access(p, os.W_OK):
                raise SystemExit(f"{p} is read-only. Make it writable, then run this again. Nothing was changed.")
        for p, data in pending.items():
            key = str(p)
            cur = read_bytes(p)
            if data is None:
                remove(p)
                sweep_tmp(p)
                self.files.pop(key, None)
                continue
            if uninstall:
                write_atomic(p, data)
                sweep_tmp(p)
                self.files.pop(key, None)
                continue
            rec = self.files.get(key)
            fresh = False
            if cur is not None and self.backup_ok.get(p, True) and (self.fresh or not backup_path(p).exists()):
                write_atomic(backup_path(p), cur)
                fresh = True
            if rec and not self.fresh:
                pristine = bool(rec.get("pristine")) and (
                    sha(cur) == rec.get("sha") if cur is not None else bool(rec.get("created")))
                created = bool(rec.get("created"))
            else:
                pristine, created = cur is None or fresh, cur is None
            dirs = self.state.setdefault("created_dirs", [])
            d = p.parent
            while not d.exists() and d != d.parent:
                if str(d) not in dirs:
                    dirs.append(str(d))
                d = d.parent
            write_atomic(p, data)
            self.files[key] = dict(rec or {}, sha=sha(data), pristine=pristine, created=created)
            if self.pokemmo:
                self.save_state(final=False)  # an interrupted run still knows what it wrote
        if uninstall:
            for b in self.drop_backups:
                remove(b)
            if self.state_path:
                remove(self.state_path)
                sweep_tmp(self.state_path)
        elif self.pokemmo:
            self.save_state()

    def save_state(self, final=True):
        if final:
            self.state["version"] = VERSION
        write_atomic(self.state_path, json.dumps(self.state, indent=2, sort_keys=True).encode() + b"\n")
