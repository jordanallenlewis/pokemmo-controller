"""Writes tests/golden/plan-parity.json: what the Python install Plan (tools/common.py) does to a folder
for a list of steps (first install, update, someone else edits a file, uninstall, ...). The Go helper must
do the same (helper/plan_test.go). Run with --write after a deliberate change to common.py;
test_plan_golden fails when the file is stale."""
import base64, json, sys, tempfile
from pathlib import Path

import helpers  # noqa: F401
import common as C

OUT = Path(__file__).resolve().parent / "golden" / "plan-parity.json"
B = lambda s: s.encode()

MAIN = "config/main.properties"
OTHER = "steam/layout.vdf"
NEWF = "deep/new/dir/file.txt"

SCENARIOS = {
    "fresh install, update, uninstall": [
        {"op": "write", "file": MAIN, "text": "a=1\r\nb=2\r\n"},
        {"op": "plan", "puts": [{"file": MAIN, "text": "a=1\r\nb=2\r\nc=3\r\n"}, {"file": NEWF, "text": "hello"}]},
        {"op": "exact", "file": MAIN}, {"op": "exact", "file": NEWF},
        {"op": "plan", "puts": [{"file": MAIN, "text": "a=1\r\nb=2\r\nc=4\r\n"}, {"file": NEWF, "text": "hello2"}]},
        {"op": "exact", "file": MAIN},
        {"op": "plan", "uninstall": True, "restore_exact": [MAIN], "deletes": [NEWF], "drop_backups": [MAIN]},
    ],
    "someone else edits the file after install": [
        {"op": "write", "file": MAIN, "text": "a=1\n"},
        {"op": "plan", "puts": [{"file": MAIN, "text": "a=1\nc=3\n"}]},
        {"op": "write", "file": MAIN, "text": "a=1\nc=3\nz=9\n"},
        {"op": "exact", "file": MAIN},
        {"op": "plan", "puts": [{"file": MAIN, "text": "a=1\nc=4\nz=9\n"}]},
        {"op": "exact", "file": MAIN},
    ],
    "backup_ok false keeps no backup": [
        {"op": "write", "file": MAIN, "text": "already ours\n"},
        {"op": "plan", "puts": [{"file": MAIN, "text": "already ours v2\n", "backup_ok": False}]},
    ],
    "fresh run replaces a stale backup": [
        {"op": "write", "file": MAIN, "text": "orig\n"},
        {"op": "write", "file": MAIN + C.SUFFIX, "text": "stale old backup\n"},
        {"op": "plan", "fresh": True, "puts": [{"file": MAIN, "text": "new\n"}]},
    ],
    "created file is removed, not restored": [
        {"op": "plan", "puts": [{"file": OTHER, "text": "layout"}]},
        {"op": "exact", "file": OTHER},
        {"op": "plan", "uninstall": True, "deletes": [OTHER]},
    ],
    "unchanged put writes nothing": [
        {"op": "write", "file": MAIN, "text": "same\n"},
        {"op": "plan", "puts": [{"file": MAIN, "text": "same\n"}]},
        {"op": "plan", "puts": [{"file": MAIN, "text": "same\n"}]},
    ],
}


def norm(s, root):
    return s.replace(root, "$ROOT").replace("\\", "/")


def snapshot(root):
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.endswith(".tmp"):
            rel = p.relative_to(root).as_posix()
            data = p.read_bytes()
            if rel == "config/" + C.STATE_NAME:
                st = json.loads(data)
                st["files"] = {norm(k, str(root)): v for k, v in st.get("files", {}).items()}
                st["created_dirs"] = [norm(d, str(root)) for d in st.get("created_dirs", [])]
                files[rel] = {"state": st}
            else:
                files[rel] = {"b64": base64.b64encode(data).decode()}
    return files


def run(steps):
    out = []
    with tempfile.TemporaryDirectory() as d:
        root = Path(d).resolve()
        for st in steps:
            rec = dict(st)
            f = root / st["file"] if "file" in st else None
            if st["op"] == "write":
                C.write_atomic(f, B(st["text"]))
            elif st["op"] == "exact":
                plan = C.Plan(root)
                r = plan.exact_original(f)
                rec["result"] = "differs" if r is False else (None if r is None else base64.b64encode(r).decode())
            elif st["op"] == "plan":
                plan = C.Plan(root)
                plan.fresh = bool(st.get("fresh"))
                uninstall = bool(st.get("uninstall"))
                for m in st.get("restore_exact", []):
                    orig = plan.exact_original(root / m)
                    if orig is not False:
                        plan.put(root / m, orig) if orig is not None else plan.delete(root / m)
                for p in st.get("puts", []):
                    plan.put(root / p["file"], B(p["text"]), p.get("backup_ok", True))
                for p in st.get("deletes", []):
                    plan.delete(root / p)
                plan.drop_backups = [C.backup_path(root / p) for p in st.get("drop_backups", [])]
                rec["pending"] = sorted(norm(str(p), str(root)) for p in plan.pending())
                plan.commit(uninstall=uninstall)
            rec["after"] = snapshot(root)
            out.append(rec)
    return out


def dump():
    cases = [{"name": n, "steps": run(s)} for n, s in SCENARIOS.items()]
    return json.dumps({"version": C.VERSION, "cases": cases}, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_bytes(dump().encode())
        print("wrote", OUT)
    else:
        print(dump())
