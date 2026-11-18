"""Writes the frozen behaviour goldens under spec/golden/ from the Python tools (FOUNDATION 7.2, M0).

    spec/golden/sandbox-trees.json   file trees after install, rerun, uninstall, each scenario
    spec/golden/records.json         install records written today, plus the migration rules

The Rust port (M2/M3) must produce the same trees from the same sandbox. Run with --write after
a deliberate change; tests/test_spec.py fails when the file is stale.

Normalising (so a tree is the same on any machine): the sandbox root becomes <ROOT> and the
tool version <VERSION>. A file whose bytes hold the root (the Steam shortcut list and the
install record: the shortcut's appid is derived from its path) is listed with "path": true
and no hash; the install record is stored parsed, keys normalised, with those hashes left out.
"""
import hashlib
import os, json, re, sys
from pathlib import Path

import helpers
from helpers import Sandbox

OUT_DIR = helpers.ROOT / "spec" / "golden"
VERSION = None


def _version():
    global VERSION
    if VERSION is None:
        import common
        VERSION = common.VERSION
    return VERSION


def _root_forms(root):
    """Every spelling of the sandbox root a program may print: as made (on Windows the 8.3 short
    temp path, RUNNER~1), resolved (long), and each with forward slashes."""
    forms = set()
    for r in (root, Path(os.path.abspath(root)), Path(root).resolve()):
        forms |= {str(r), r.as_posix()}
    return sorted(forms, key=len, reverse=True)


def _norm_text(text, root):
    for form in _root_forms(root):
        text = text.replace(form, "<ROOT>")
    text = text.replace(_version(), "<VERSION>")
    text = re.sub(r"appid -?\d+", "appid <APPID>", text)
    return text.replace("\\", "/")


def _walk(x, root):
    if isinstance(x, str):
        return _norm_text(x, root)
    if isinstance(x, list):
        return [_walk(i, root) for i in x]
    if isinstance(x, dict):
        return {_norm_text(k, root): _walk(v, root) for k, v in x.items()}
    return x


def _norm_record(raw, root):
    raw_rec = json.loads(raw.decode("utf-8"))
    holds_root = set()
    for k in raw_rec.get("files", {}):
        try:
            data = Path(k).read_bytes()
        except OSError:
            continue
        if any(f.encode() in data for f in _root_forms(root)):
            holds_root.add(_norm_text(k, root))
    rec = _walk(raw_rec, root)
    for k, v in rec.get("files", {}).items():
        if k in holds_root:
            v.pop("sha", None)  # holds the root path, so its hash differs per machine
    if "created_dirs" in rec:
        rec["created_dirs"] = sorted(rec["created_dirs"])
    return rec


def tree(sb):
    """{relative path: sha-256 of the bytes, or null for an empty folder, or {"path": true}}."""
    root = sb.root
    out = {}
    for rel, data in sb.snapshot().items():
        if data is None:
            out[rel] = None
        elif rel.endswith("config/pokemmo-controller.json"):
            out[rel] = {"path": True}
        elif any(f.encode() in data for f in _root_forms(root)):
            out[rel] = {"path": True}
        else:
            out[rel] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    return out


def record(sb):
    p = sb.pokemmo / "config" / "pokemmo-controller.json"
    if not p.exists():
        return None
    return _norm_record(p.read_bytes(), sb.root)


def step(sb, label, *args, **kw):
    r = sb.setup(*args, check=False, **kw)
    root = sb.root
    lines = [_norm_text(l, root).rstrip() for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return {"step": label, "argv": [_norm_text(a, root) for a in args], "exit": r.returncode, "output": lines,
            "tree": tree(sb), "record": record(sb)}


def old_step(sb, label, tag):
    """Install with the tools as they were at a release tag (needs the tags: CI checks out full history)."""
    import subprocess, tempfile, sys, io, tarfile
    tar = subprocess.run(["git", "archive", tag, "tools"], cwd=helpers.ROOT, capture_output=True)
    if tar.returncode:
        raise AssertionError(f"git archive {tag} failed (is the tag fetched?): {tar.stderr.decode()}")
    with tempfile.TemporaryDirectory(prefix="pmc-old-") as d:
        tf = tarfile.open(fileobj=io.BytesIO(tar.stdout))
        tf.extractall(d, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        cmd = [sys.executable, str(Path(d) / "tools" / "setup.py"), "--pokemmo", str(sb.pokemmo), "--steam", str(sb.steam)]
        r = subprocess.run(cmd, env=sb.env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise AssertionError(f"{tag} install failed:\n{r.stdout}\n{r.stderr}")
    return {"step": label, "argv": [f"(tools at {tag})"], "exit": r.returncode, "output": [],
            "tree": tree(sb), "record": record(sb)}


def edit_props(sb, fn):
    data = sb.props.read_bytes()
    nl = "\r\n" if b"\r\n" in data else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    sb.props.write_bytes(fn(text).replace("\n", nl).encode("utf-8"))


def scenarios():
    import layout as L
    out = {}

    def run(name, build, steps):
        sb = Sandbox(**build)
        try:
            res = [{"step": "before", "tree": tree(sb), "record": record(sb)}]
            for s in steps:
                res.append(s(sb))
            out[name] = res
        finally:
            sb.cleanup()

    run("install-rerun-uninstall", {}, [
        lambda sb: step(sb, "install"), lambda sb: step(sb, "rerun"),
        lambda sb: step(sb, "uninstall", "--uninstall")])
    for tag in ("v1.1.0", "v1.2.0"):
        run(f"update-from-{tag}", {}, [
            lambda sb, tag=tag: old_step(sb, f"install with {tag}", tag),
            lambda sb: step(sb, "update to this version"), lambda sb: step(sb, "uninstall", "--uninstall")])
    run("lf-line-endings", {"crlf": False}, [
        lambda sb: step(sb, "install"), lambda sb: step(sb, "uninstall", "--uninstall")])
    run("no-wheel", {}, [
        lambda sb: step(sb, "install", "--no-wheel"), lambda sb: step(sb, "uninstall", "--uninstall")])
    run("switch-positional", {}, [
        lambda sb: step(sb, "install", "--switch-positional"),
        lambda sb: step(sb, "uninstall", "--uninstall")])
    run("no-steam", {"steam": False}, [
        lambda sb: step(sb, "install", steam=False), lambda sb: step(sb, "uninstall", "--uninstall", steam=False)])

    def custom(sb):
        lay = L.default_layout()
        lay["binds"]["KEY_INVENTORY"] = {"button": 4}
        lay["binds"]["KEY_HOTBAR_5"] = {"button": 10}   # the Focus Ring / Hotbar 5 swap
        lay["name"] = "golden"
        f = sb.root / "layout.json"
        f.write_text(L.dumps(lay), encoding="utf-8")
        return step(sb, "install custom layout", "--layout", str(f))
    run("custom-layout-focus-ring-hotbar5-swap", {}, [
        custom, lambda sb: step(sb, "reset layout", "--reset-layout"),
        lambda sb: step(sb, "uninstall", "--uninstall")])

    def pushed_trigger(sb):
        lay = L.default_layout()
        lay["binds"]["KEY_NEXT"] = {"axis": 5, "positive": True}
        f = sb.root / "layout.json"
        f.write_text(L.dumps(lay), encoding="utf-8")
        return step(sb, "install pushed-trigger layout", "--layout", str(f))
    run("pushed-trigger-layout", {}, [pushed_trigger, lambda sb: step(sb, "uninstall", "--uninstall")])

    def edit_after(sb):
        edit_props(sb, lambda t: t.replace("client.ui.theme=dark", "client.ui.theme=light")
                   + "client.controls.gdx.mine=99\n")
        return step(sb, "uninstall after the player edited the file", "--uninstall")
    run("uninstall-three-way-merge", {}, [lambda sb: step(sb, "install"), edit_after])

    def edit_crlf(sb):
        edit_props(sb, lambda t: t)  # rewrite with the file's own line endings: bytes unchanged
        return step(sb, "uninstall", "--uninstall")
    run("uninstall-after-crlf-collapse", {"crlf": True}, [lambda sb: step(sb, "install"), edit_crlf])

    def lf_collapse(sb):
        sb.props.write_bytes(sb.props.read_bytes().replace(b"\r\n", b"\n"))
        return step(sb, "uninstall after the editor changed CRLF to LF", "--uninstall")
    run("uninstall-crlf-collapsed-to-lf", {"crlf": True}, [lambda sb: step(sb, "install"), lf_collapse])
    return out


def records():
    """The install records written today, and the rules for reading older ones (docs/FOUNDATION 3.4)."""
    sb = Sandbox()
    try:
        sb.setup()
        current = record(sb)
    finally:
        sb.cleanup()
    return {
        "schema": "pmc.golden.records/1",
        "current_python_record": current,
        "reading_rules": [
            {"id": "no-record-field", "given": {"record_format": None}, "read_as": 1,
             "note": "A record without record_format is version 1 and is read by today's rules."},
            {"id": "missing-record", "given": "no record file", "read_as": "v1.0 install",
             "note": "A missing record means a v1.0 install."},
            {"id": "newer-record", "given": {"record_format": 3}, "engine": "refuses to write",
             "uninstall": "still works from files{} alone", "exit": 6},
        ],
        "locked_keys": ["version", "files", "names", "extra_names", "switch_positional", "layout", "screen",
                        "screen_manual", "follow", "autostart", "app", "shortcuts_added", "created_dirs"],
        "file_entry_keys": ["sha", "pristine", "created"],
    }


FOLLOW_SEQUENCES = [
    ("settles after three equal samples", None, [[3840, 2160]] * 3 + [[1920, 1080]] * 3),
    ("fast flap 4K 1080p 1440p 4K leaves no stale size", [3840, 2160],
     [[3840, 2160], [1920, 1080], [1920, 1080], [2560, 1440], [3840, 2160], [3840, 2160], [3840, 2160]]),
    ("junk samples are ignored", [1920, 1080],
     [None, [0, 0], [-5, 100], [100, 100], [1e12, 1e12], [1920.5, 1080], [True, False], "x", [2560, 1440], [2560, 1440],
      [2560, 1440]]),
    ("the 640x480 login window is skipped", [1920, 1080], [[640, 480]] * 5 + [[1920, 1080]] * 3),
    ("a half-finished resize (wider than 8 to 1) is skipped", [1920, 1080], [[8000, 600]] * 4),
    ("a move to a monitor at the same resolution writes nothing", [2560, 1440], [[2560, 1440]] * 6),
    ("2560x1440 to 2560x1400 and back, as it behaves today", [2560, 1440], [[2560, 1400]] * 3 + [[2560, 1440]] * 3),
    ("whole-number floats count as integers", None, [[1920.0, 1080.0]] * 3),
]


def follower_sequences():
    import fit
    out = []
    for label, applied, samples in FOLLOW_SEQUENCES:
        f = fit.Follower(tuple(applied) if applied else None)
        writes = []
        for smp in samples:
            r = f.feed(tuple(smp) if isinstance(smp, list) else smp)
            writes.append(list(r) if r else None)
        out.append({"label": label, "applied": applied, "settle": fit.SETTLE, "samples": samples, "writes": writes})
    return {"schema": "pmc.golden.follower/1", "constants": {"settle": fit.SETTLE, "login_size": list(fit.LOGIN_SIZE),
            "tolerance": fit.TOLERANCE, "max_aspect": fit.MAX_ASPECT}, "sequences": out}


def build():
    return {"follower-sequences.json": follower_sequences(), "sandbox-trees.json": {"schema": "pmc.golden.trees/1", "scenarios": scenarios()},
            "records.json": records()}


def dump(doc):
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    docs = build()
    if "--write" in sys.argv:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for name, doc in docs.items():
            (OUT_DIR / name).write_text(dump(doc), encoding="utf-8", newline="\n")
            print("wrote", OUT_DIR / name)
    else:
        for name, doc in docs.items():
            print(name, len(dump(doc)), "bytes")


if __name__ == "__main__":
    main()
