"""Writes tests/golden/shortcuts-parity.json: how the Python tool (tools/install_wheel.py) reads and
writes Steam's shortcuts.vdf and adds the "PokeMMO" non-Steam shortcut (shortcut_plan), for several
files, backups and install records. The Go helper must give the same bytes and notes
(helper/shortcuts_test.go). Run with --write after a deliberate change to install_wheel.py;
test_shortcuts_golden fails when the file is stale."""
import base64, json, sys
from pathlib import Path

import helpers  # noqa: F401
import install_wheel as W

OUT = Path(__file__).resolve().parent / "golden" / "shortcuts-parity.json"
USERDIR = Path("USERDIR")

T_WIN = ('"C:\\Games\\PokeMMO\\PokeMMO.exe"', '"C:\\Games\\PokeMMO\\"', "")
T_MAC = ('"/Applications/PokeMMO.app"', '"/Applications/"', "")
T_FLATPAK = ('"/usr/bin/flatpak"', '"/usr/bin/"', "run com.pokemmo.PokeMMO")
T_LINUX = ('"/home/deck/PokeMMO/PokeMMO.sh"', '"/home/deck/PokeMMO/"', "")
T_ACCENT = ('"/home/jos\u00e9/PokeMMO/PokeMMO.sh"', '"/home/jos\u00e9/PokeMMO/"', "")


def game(name, exe, appid=-1234567, lower=False, **extra):
    d = {"appid": appid, ("appname" if lower else "AppName"): name, ("exe" if lower else "Exe"): exe,
         "StartDir": '"/games/"', "LaunchOptions": "", "IsHidden": 0, "tags": {"0": "favorite"}}
    d.update(extra)
    return d


def vdf(*entries, keys=None):
    keys = keys or [str(i) for i in range(len(entries))]
    return W.write_shortcuts(dict(zip(keys, entries)))


OTHER = game("Other Game", '"/games/other"')
THIRD = game("Third", '"/games/third"', appid=-99)
OURS = game("PokeMMO", T_LINUX[0], appid=-2000000000)
OURS_LOWER = game("PokeMMO", T_LINUX[0], lower=True)
WITH_RAW = game("Raw Fields", '"/games/raw"', Ratio=W.Raw(3, b"\x00\x00\x80\x3f"), Big=W.Raw(7, bytes(range(8))))
ODD_NAME = game("Caf\udce9", '"/games/caf"')        # a name that is not valid UTF-8 (byte 0xE9)

PARSE = [
    ("empty shortcuts", vdf()),
    ("two games", vdf(OTHER, THIRD)),
    ("ours present", vdf(OTHER, OURS)),
    ("lowercase keys", vdf(OURS_LOWER)),
    ("raw fields kept", vdf(WITH_RAW)),
    ("name not utf-8", vdf(ODD_NAME)),
    ("gaps and a word key", vdf(OTHER, THIRD, OTHER, keys=["0", "5", "x"])),
    ("trailing bytes after the file", vdf(OTHER) + b"\x00junk"),
    ("other top-level key", b"\x00shortcuts\x00\x08\x01note\x00hi\x00\x08"),
    ("empty file", b""),
    ("garbage", b"not a vdf at all"),
    ("cut short", vdf(OTHER)[:-7]),
    ("unknown type", b"\x00shortcuts\x00\x09k\x00\x08\x08"),
    ("int cut short", b"\x00shortcuts\x00\x02n\x00\x01\x02"),
    ("duplicate key", b"\x00shortcuts\x00\x010\x00a\x00\x010\x00b\x00\x08\x08"),
    ("shortcuts is text", b"\x01shortcuts\x00x\x00\x08"),
    ("no shortcuts key", b"\x00other\x00\x08\x08"),
    ("ends with type 11", b"\x00shortcuts\x00\x0b\x08"),
]

SCENARIOS = [
    {"label": "fresh install, no file", "data": None, "fresh": True, "target": T_LINUX},
    {"label": "fresh install, empty file", "data": b"", "fresh": True, "target": T_LINUX},
    {"label": "update adds after other games", "data": vdf(OTHER, THIRD), "version": "1.3.0", "target": T_WIN},
    {"label": "mac target", "data": vdf(OTHER), "version": "1.3.0", "target": T_MAC},
    {"label": "flatpak target", "data": vdf(), "version": "1.3.0", "target": T_FLATPAK},
    {"label": "accented path", "data": None, "version": "1.3.0", "target": T_ACCENT},
    {"label": "next key after gaps", "data": vdf(OTHER, THIRD, OTHER, keys=["0", "5", "x"]), "version": "1.3.0",
     "target": T_LINUX},
    {"label": "raw fields kept on add", "data": vdf(WITH_RAW, ODD_NAME), "version": "1.3.0", "target": T_LINUX},
    {"label": "already there", "data": vdf(OTHER, OURS), "version": "1.3.0", "target": T_LINUX},
    {"label": "already there, lowercase", "data": vdf(OURS_LOWER), "version": "1.3.0", "target": T_LINUX},
    {"label": "already recorded as ours", "data": vdf(OTHER), "version": "1.3.0", "added_before": True,
     "target": T_LINUX},
    {"label": "trailing bytes dropped on add", "data": vdf(OTHER) + b"\x00junk", "version": "1.3.0",
     "target": T_LINUX},
    {"label": "unreadable file", "data": b"garbage", "version": "1.3.0", "target": T_LINUX},
    {"label": "unreadable backup", "data": vdf(OTHER), "bak": b"garbage", "version": "1.3.0", "target": T_LINUX},
    {"label": "empty backup", "data": vdf(OTHER), "bak": b"", "version": "1.3.0", "target": T_LINUX},
    {"label": "legacy: overwritten game is restored",
     "data": vdf(OURS, THIRD), "bak": vdf(OTHER, THIRD), "target": T_LINUX},
    {"label": "legacy: two lost, keys taken",
     "data": vdf(OURS), "bak": vdf(OTHER, THIRD, keys=["0", "3"]), "target": T_LINUX},
    {"label": "legacy: restored game sorts before ours",
     "data": vdf(OURS, keys=["5"]), "bak": vdf(OTHER, keys=["0"]), "target": T_LINUX},
    {"label": "legacy: restore, then add ours", "data": vdf(THIRD), "bak": vdf(OTHER, THIRD), "target": T_WIN},
    {"label": "empty backup, ours removed in Steam", "data": vdf(), "bak": b"", "version": "1.3.0",
     "added_before": True, "target": T_LINUX},
    {"label": "legacy: ours was in the backup", "data": vdf(OTHER, OURS), "bak": vdf(OTHER, OURS),
     "target": T_LINUX},
    {"label": "legacy: nothing lost, ours missing", "data": vdf(OTHER), "bak": vdf(OTHER), "target": T_LINUX},
    {"label": "legacy, no backup", "data": vdf(OTHER, OURS), "target": T_LINUX},
    {"label": "fresh is not legacy", "data": vdf(OURS), "bak": vdf(OTHER), "fresh": True, "target": T_LINUX},
    {"label": "empty version is legacy", "data": vdf(OURS), "bak": vdf(OTHER), "version": "", "target": T_LINUX},
]


class FakePlan:
    def __init__(self, data, state, fresh):
        self.data, self.state, self.fresh, self.notes, self.put_data = data, state, fresh, [], None

    def current(self, p):
        return self.data

    def put(self, p, data, backup_ok=True):
        self.data = self.put_data = data


def b64(b):
    return None if b is None else base64.b64encode(b).decode("ascii")


def norm(s):
    return str(s).replace(str(USERDIR), "$U").replace("\\", "/")


def run(sc):
    path = USERDIR / "config" / "shortcuts.vdf"
    state = {}
    if sc.get("version") is not None:
        state["version"] = sc["version"]
    if sc.get("added_before"):
        state["shortcuts_added"] = [str(path)]
    p = FakePlan(sc["data"], state, sc.get("fresh", False))
    real_read, real_target = W.read_bytes, W.shortcut_target
    W.read_bytes = lambda q: sc.get("bak")
    W.shortcut_target = lambda pm: sc["target"]
    try:
        W.shortcut_plan(p, USERDIR, Path("PM"))
    finally:
        W.read_bytes, W.shortcut_target = real_read, real_target
    return {"label": sc["label"], "data": b64(sc["data"]), "bak": b64(sc.get("bak")),
            "version": sc.get("version"), "fresh": sc.get("fresh", False),
            "added_before": sc.get("added_before", False), "target": list(sc["target"]),
            "put": b64(p.put_data), "notes": [norm(n) for n in p.notes],
            "added": [norm(a) for a in p.state["shortcuts_added"]]}


def build():
    parse = []
    for label, data in PARSE:
        try:
            parse.append({"label": label, "data": b64(data), "ok": True, "rewritten": b64(W.write_shortcuts(W.read_shortcuts(data)))})
        except ValueError:
            parse.append({"label": label, "data": b64(data), "ok": False, "rewritten": None})
    return {"parse": parse, "plans": [run(sc) for sc in SCENARIOS]}


def dump():
    return json.dumps(build(), indent=1, ensure_ascii=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_text(dump(), encoding="utf-8", newline="\n")
        print("wrote", OUT)
    else:
        sys.stdout.write(dump())
