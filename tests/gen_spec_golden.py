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
import hashlib, json, re, sys
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


def _norm_text(text, root):
    text = text.replace(str(root), "<ROOT>").replace(root.as_posix(), "<ROOT>")
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
    rec = _walk(json.loads(raw.decode("utf-8")), root)
    for k, v in rec.get("files", {}).items():
        if k.endswith("shortcuts.vdf"):
            v.pop("sha", None)  # holds the root path, so its hash differs per machine
    if "created_dirs" in rec:
        rec["created_dirs"] = sorted(rec["created_dirs"])
    return rec


def tree(sb):
    """{relative path: sha-256 of the bytes, or null for an empty folder, or {"path": true}}."""
    root = sb.root.resolve()
    out = {}
    for rel, data in sb.snapshot().items():
        if data is None:
            out[rel] = None
        elif rel.endswith("config/pokemmo-controller.json"):
            out[rel] = {"path": True}
        elif str(root).encode() in data or root.as_posix().encode() in data:
            out[rel] = {"path": True}
        else:
            out[rel] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    return out


def record(sb):
    p = sb.pokemmo / "config" / "pokemmo-controller.json"
    if not p.exists():
        return None
    return _norm_record(p.read_bytes(), sb.root.resolve())


def step(sb, label, *args, **kw):
    r = sb.setup(*args, check=False, **kw)
    root = sb.root.resolve()
    lines = [_norm_text(l, root).rstrip() for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return {"step": label, "argv": [_norm_text(a, root) for a in args], "exit": r.returncode, "output": lines,
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


def build():
    return {"sandbox-trees.json": {"schema": "pmc.golden.trees/1", "scenarios": scenarios()},
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
