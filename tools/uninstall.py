"""Undo apply_native.py and install_wheel.py, touching only what they changed.

Close PokeMMO and Steam, then:  python tools/uninstall.py
- PokeMMO main.properties: the controller map, controller-support switch and
  wheel keyboard binds go back to their values in the pre-install backup;
  every other setting you changed since is kept.
- Steam: removes the "PokeMMO" shortcut and the wheel layouts.
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_wheel import (running, parse_bvdf, dump_bvdf, KEYBOARD_BINDS,  # noqa: E402
                           SHORTCUT_NAME, CONFIG_DIR_NAME)

SUFFIX = ".bak-pokemmo-controller"
TOUCHED = set(KEYBOARD_BINDS) | {"client.controls.controller_input_maps_gdx_2",
                                 "client.input.controllers.enable_native_support"}


def props(path):
    return dict(l.split("=", 1) for l in path.read_text(encoding="utf-8").splitlines()
                if "=" in l and not l.startswith("#"))


def revert_properties(path: Path):
    bak = path.with_name(path.name + SUFFIX)
    if not bak.exists():
        print(f"no backup for {path}, left as is")
        return
    old = props(bak)
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        k = line.split("=", 1)[0]
        if k in TOUCHED:
            if k in old:
                out.append(f"{k}={old[k]}")
            continue  # key did not exist before install
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"reverted controller settings in {path}")


def remove_shortcut(p: Path):
    if not p.exists():
        return
    data, _ = parse_bvdf(p.read_bytes())
    sc = data.get("shortcuts", {})
    keep = [v for v in sc.values() if v.get("AppName", v.get("appname")) != SHORTCUT_NAME]
    if len(keep) == len(sc):
        return
    p.write_bytes(b"\0shortcuts\0" + dump_bvdf({str(i): v for i, v in enumerate(keep)}) + b"\x08")
    print(f"removed Steam shortcut {SHORTCUT_NAME}")


def remove_layouts(cfg: Path):
    for t in ("controller_xboxone", "controller_xbox360"):
        f = cfg / CONFIG_DIR_NAME / f"{t}.vdf"
        if f.exists():
            f.unlink()
        cs = cfg / f"configset_{t}.vdf"
        if cs.exists():
            txt = cs.read_text(encoding="utf-8")
            new = re.sub(r'\t"' + CONFIG_DIR_NAME + r'"\n\t\{.*?\n\t\}\n', "", txt, flags=re.S)
            if new != txt:
                cs.write_text(new, encoding="utf-8")
                print(f"removed wheel layout ({t})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokemmo", default=r"C:\Program Files\PokeMMO")
    ap.add_argument("--steam", default=r"C:\Program Files (x86)\Steam")
    a = ap.parse_args()
    busy = [e for e in ("PokeMMO.exe", "steam.exe") if running(e)]
    if busy:
        sys.exit(f"Close {' and '.join(busy)} first; both rewrite these files on exit.")
    pm, steam = Path(a.pokemmo), Path(a.steam)
    revert_properties(pm / "config" / "main.properties")
    for u in (steam / "userdata").iterdir():
        if u.name.isdigit():
            remove_shortcut(u / "config" / "shortcuts.vdf")
    cfgs = steam / "steamapps" / "common" / "Steam Controller Configs"
    if cfgs.exists():
        for acct in cfgs.iterdir():
            remove_layouts(acct / "config")
    print("Done.")


if __name__ == "__main__":
    main()
