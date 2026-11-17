"""Writes tests/golden/native-parity.json: what the Python tools/apply_native.py says about pad
names, layouts and map entries. The Go helper must say the same (helper/nativemap_test.go).
Run with --write after a deliberate change to apply_native.py; test_native_golden fails when
the file is stale."""
import json, random, sys
from pathlib import Path

import helpers  # noqa: F401
import apply_native as A
import layout as L
import gen_layout_golden as GL

OUT = Path(__file__).resolve().parent / "golden" / "native-parity.json"

EXTRA_NAMES = ["Pro Controller", "Nintendo Foo", "My Pad; odd|name", "Café Pad", " lead", "back\\slash", "x=y"]
LOGS = [
    "", "nothing here\n",
    "Controller Xbox Wireless Controller ( ax 6 btn 15) 1 attached\n",
    "a\nController PS5 Controller ( ax 6 btn 16) was attached\nController PS5 Controller ( ax 6 btn 16) attached\n",
    "Controller Odd Pad (2) ( ax 4 btn 12) x attached\nController Odd Pad (2) ( ax 4 btn 12) y attached\n",
    "Controller  ( ax 1 btn 1) attached\n", "Controller A\nB ( ax 1 btn 1) attached\n",
    "Controller Café ( ax 2 btn 2) attached\nController Café ( ax 2 btn 2) attached\n",
]
MAPS = [
    "", "A;KEY_A,BUTTON,0", "A;KEY_A,BUTTON,0|B;KEY_B,BUTTON,1", "A\\|B;KEY_A,BUTTON,0|C;x",
    "|A;x||B;y|", ";KEY_A,BUTTON,0|N;z", "Caf\\u00E9;KEY_A,BUTTON,0", "A\\\\|B;q", "no semicolon", "A;|B",
]


def layouts():
    out = [None]
    for label, text in GL.texts():
        try:
            lay = L.loads(text)
        except L.LayoutError:
            continue
        out.append((label, lay))
    return out


def build():
    names = A.CONTROLLER_NAMES + EXTRA_NAMES
    lays = layouts()
    cust = [(lbl, L.native_binds(lay)) for lbl, lay in lays[1:]]
    entries = []
    for n in names:
        for nl in (True, False):
            entries.append({"name": n, "labels": nl, "layout": None, "entry": A.encode_one(n, nl)})
    for lbl, binds in cust:
        for n in ["Xbox Series X Controller", "Nintendo Switch Pro Controller", "Pro Controller"]:
            for nl in (True, False):
                entries.append({"name": n, "labels": nl, "layout": lbl, "entry": A.encode_one(n, nl, binds)})
    swap = dict(cust)["swap buttons"]
    extra = sorted(sorted(s) for s in A.layout_sets(swap))
    pool = [e["entry"] for e in entries][:60] + [
        A.encode_one("X", True, dict(A.LEGACY_LAYOUT)), A.encode_one("Pro Controller", True, dict(A.LEGACY_LAYOUT)),
        "X", "X;", "X;KEY_A,BUTTON,0", "", ";;",
    ]
    rnd = random.Random(7)
    for e in list(pool[:6]):
        parts = e.split(";")
        rest = parts[1:]
        rnd.shuffle(rest)
        pool.append(";".join(parts[:1] + rest))
        pool.append(";".join(parts + ["KEY_X,BUTTON,9"]))
        pool.append(";".join(parts[:-1]))
    pool.append(A.encode_one("Pro Controller", True, swap))
    pool.append(A.encode_one("Pro Controller", False, swap))
    ours = [{"entry": e, "default": A.is_ours(e), "custom": A.is_ours(e, {frozenset(x) for x in extra})} for e in pool]
    return {
        "names": names,
        "default_sets": sorted(sorted(s) for s in A.layout_sets(dict(A.LAYOUT))),
        "legacy_sets": sorted(sorted(s) for s in A.layout_sets(A.LEGACY_LAYOUT)),
        "custom_extra": extra,
        "entries": entries, "ours": ours,
        "split": [{"value": m, "entries": [[k, v] for k, v in A.split_entries(m).items()]} for m in MAPS],
        "logged": [{"text": t, "names": [m.group(1) for m in A.LOG_LINE.finditer(t)]} for t in LOGS],
        "is_nintendo": [[n, A.is_nintendo(n)] for n in names],
        "controller_names": A.CONTROLLER_NAMES,
    }


def dump():
    return json.dumps(build(), indent=1, ensure_ascii=True, sort_keys=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_bytes(dump().encode())
        print("wrote", OUT)
    else:
        print(dump())
