"""Undo apply_native.py and install_wheel.py, touching only what they changed.

Close PokeMMO and Steam, then:  python tools/uninstall.py
- If nothing else changed a file since the install, its original bytes come
  back exactly (from the *.bak-pokemmo-controller backup).
- Otherwise only this project's parts are taken out:
  PokeMMO main.properties: controller maps that still hold this layout go back
  to what you had before (or are removed), and the controller switch and wheel
  keys go back if they still hold the values set here. Everything else you
  changed since, including binds you made by hand, is kept.
  Steam: the "PokeMMO" shortcut this project added, its wheel layouts and their
  configset entries are removed; a layout or shortcut you had before comes back.
- Backups and the install record are deleted at the end.
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (MAP_KEY, NATIVE_KEY, Plan, backup_path, decode, encode,  # noqa: E402
                    get_prop, join_lines, read_bytes, set_props, split_lines)
from apply_native import custom_sets, installed, is_ours, props_path, split_entries  # noqa: E402
from install_wheel import (BLOCK, CONFIG_DIR_NAME, CONTROLLER_TYPES, KEYBOARD_BINDS,  # noqa: E402
                           LAYOUT_TITLE, OUR_BLOCK, configset_with_block, is_pokemmo_shortcut,
                           read_shortcuts, restore_lost_shortcuts, write_shortcuts)
from platforms import find_pokemmo, steam_candidates, require_closed  # noqa: E402


def _restore_exact(p, path):
    """Plan the original bytes back if only we changed path. True if planned."""
    exact = p.exact_original(path)
    if exact is False:
        return False
    if exact is None:
        p.delete(path)
    else:
        p.put(path, exact)
    return True


def _put_merged(p, path, data):
    """Plan data, or the backup's exact bytes when they only differ in line endings."""
    bak = read_bytes(backup_path(path))
    if bak is not None and decode(bak)[0] == decode(data)[0]:
        data = bak
    p.put(path, data)


def revert_properties(p, pm: Path):
    path = props_path(pm)
    bak_path = backup_path(path)
    data = read_bytes(path)
    if data is None or not (p.state.get("version") or installed(pm, custom_sets(p.state)) or bak_path.exists()):
        return
    p.drop_backups.append(bak_path)
    if _restore_exact(p, path):
        return
    text, nl = decode(data)
    lines, final = split_lines(text)
    bak = read_bytes(bak_path)
    blines = split_lines(decode(bak)[0])[0] if bak is not None else []
    want = {}
    for k, v in KEYBOARD_BINDS.items():
        if get_prop(lines, k) == str(v):  # still ours: put yours back
            want[k] = get_prop(blines, k)
    if get_prop(lines, NATIVE_KEY) == "true":
        want[NATIVE_KEY] = get_prop(blines, NATIVE_KEY)
    entries = split_entries(get_prop(lines, MAP_KEY) or "")
    old = split_entries(get_prop(blines, MAP_KEY) or "")
    keep = {}
    for n, e in entries.items():
        if not is_ours(e, custom_sets(p.state)):
            keep[n] = e          # a map you made or changed yourself
        elif n in old:
            keep[n] = old[n]     # your map from before the install
    if keep != entries:
        want[MAP_KEY] = "|".join(keep.values()) if keep or get_prop(blines, MAP_KEY) is not None else None
    for k in [k for k, v in want.items() if v == get_prop(lines, k)]:
        del want[k]
    _put_merged(p, path, encode(join_lines(set_props(lines, want), final), nl) if want else data)


def revert_shortcuts(p, path: Path, ours_ok: bool):
    data = read_bytes(path)
    bak_path = backup_path(path)
    bak = read_bytes(bak_path)
    p.drop_backups.append(bak_path)
    if data is None or _restore_exact(p, path):
        return
    try:
        sc = read_shortcuts(data)
        had = bak is not None and any(is_pokemmo_shortcut(v) for v in read_shortcuts(bak).values())
    except ValueError:
        p.notes.append(f"Could not read {path}; remove the PokeMMO shortcut in Steam by hand.")
        return
    legacy = ours_ok and not p.state.get("version")
    ours = str(path) in p.state.get("shortcuts_added", []) or (legacy and not had)
    keep = {k: v for k, v in sc.items() if not (ours and is_pokemmo_shortcut(v))}
    if legacy and bak is not None:
        restore_lost_shortcuts(keep, read_shortcuts(bak))
    if keep == sc:
        return
    rec = p.files.get(str(path), {})
    if not keep and (bak is None or rec.get("created")):
        p.delete(path)
    elif bak is not None and list(read_shortcuts(bak).values()) == list(keep.values()):
        p.put(path, bak)  # the same shortcuts as before the install: its exact bytes
    else:
        p.put(path, write_shortcuts(keep))


def revert_layouts(p, cfg: Path, ours_ok: bool):
    for t in CONTROLLER_TYPES:
        f = cfg / CONFIG_DIR_NAME / f"{t}.vdf"
        p.drop_backups.append(backup_path(f))
        data = read_bytes(f)
        if data is not None and ours_ok and not _restore_exact(p, f):
            bak = read_bytes(backup_path(f))
            if bak is not None:
                p.put(f, bak)            # the layout you had before
            elif str(f) in p.files or LAYOUT_TITLE.encode() in data:
                p.delete(f)
        cs = cfg / f"configset_{t}.vdf"
        p.drop_backups.append(backup_path(cs))
        data = read_bytes(cs)
        if data is None or not ours_ok or _restore_exact(p, cs):
            continue
        text, nl = decode(data)
        if not BLOCK.search(text):
            _put_merged(p, cs, data)
            continue
        bak = read_bytes(backup_path(cs))
        m = BLOCK.search(decode(bak)[0]) if bak is not None else None
        block = m.group(0) if m and m.group(0) != OUR_BLOCK else ""
        try:
            new = configset_with_block(text, block)
        except ValueError:
            p.notes.append(f"Could not read {cs}; remove the pokemmo entry by hand.")
            continue
        if bak is None and new.split() == ['"controller_config"', "{", "}"]:
            p.delete(cs)
        else:
            _put_merged(p, cs, encode(new, nl))


def steam_roots(p, override=None):
    roots = [Path(override).expanduser()] if override else list(steam_candidates())
    for key in p.files:
        for parent in Path(key).parents:
            if (parent / "userdata").is_dir():
                roots.append(parent)
                break
    return list(dict.fromkeys(r.resolve() for r in roots if (r / "userdata").is_dir()))


def plan(p, pm, steams):
    legacy = pm is not None and not p.state.get("version") and (
        installed(pm) or backup_path(props_path(pm)).exists())
    if pm is not None:
        revert_properties(p, pm)
    for steam in steams:
        cfgs = steam / "steamapps" / "common" / "Steam Controller Configs"
        accounts = [a for a in cfgs.iterdir() if a.is_dir()] if cfgs.is_dir() else []
        ours_ok = bool(p.state.get("version")) or legacy or any(
            LAYOUT_TITLE.encode() in (read_bytes(a / "config" / CONFIG_DIR_NAME / f"{t}.vdf") or b"")
            for a in accounts for t in CONTROLLER_TYPES)
        for u in sorted((steam / "userdata").iterdir()):
            if u.name.isdigit():
                revert_shortcuts(p, u / "config" / "shortcuts.vdf", ours_ok)
        for acct in accounts:
            revert_layouts(p, acct / "config", ours_ok)


def remove_empty_dirs(steams, created=()):
    """Remove folders the install created (and empty layout folders older versions left)."""
    dirs = [Path(d) for d in created]
    for steam in steams:
        cfgs = steam / "steamapps" / "common" / "Steam Controller Configs"
        for pattern in (f"*/config/{CONFIG_DIR_NAME}", "*/config", "*"):
            dirs += cfgs.glob(pattern) if cfgs.is_dir() else []
        dirs += (steam / "userdata").glob("*/config")
    for d in sorted(set(dirs), key=lambda d: len(d.parts), reverse=True):
        try:
            d.rmdir()  # only if empty
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--steam", help="Steam folder (holds userdata/)")
    a = ap.parse_args()
    require_closed(steam=True)
    try:
        pm = find_pokemmo(a.pokemmo)
    except SystemExit:
        pm = None
        print("PokeMMO not found: cleaning up Steam only.")
    p = Plan(pm)
    steams = steam_roots(p, a.steam)
    plan(p, pm, steams)
    p.commit(uninstall=True)
    remove_empty_dirs(steams, p.state.get("created_dirs", []))
    print("Done.")


if __name__ == "__main__":
    main()
