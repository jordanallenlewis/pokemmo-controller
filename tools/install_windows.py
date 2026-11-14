"""Install the PokeMMO Xbox layout on a Windows PC.

Close PokeMMO and Steam first. Then run:  python tools/install_windows.py
What it does (backs up every file it touches as *.bak-pokemmo-controller):
  1. PokeMMO config/main.properties: turns the client's own controller support off
     (Steam Input drives keyboard+mouse instead, so inputs never double up) and
     binds Bag = Q and Game Menu = M, the two actions that ship unbound.
  2. Steam: adds a non-Steam shortcut "PokeMMO", installs the layout as its
     Xbox controller config.
Options: --pokemmo "C:\\Program Files\\PokeMMO"  --steam "C:\\Program Files (x86)\\Steam"
"""
import argparse, binascii, re, shutil, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "steam" / "controller_xboxone.vdf"
SHORTCUT_NAME = "PokeMMO"
CONFIG_DIR_NAME = "pokemmo"  # Steam keys non-Steam configs by lower-case name

# libGDX key codes the layout relies on
GAME_BINDS = {
    "client.controls.gdx.key_up": 51,      # W
    "client.controls.gdx.key_left": 29,    # A
    "client.controls.gdx.key_down": 47,    # S
    "client.controls.gdx.key_right": 32,   # D
    "client.controls.gdx.key_a": 33,       # E
    "client.controls.gdx.key_b": 30,       # B
    "client.controls.gdx.key_x": 52,       # X
    "client.controls.gdx.key_y": 53,       # Y
    "client.controls.gdx.bag": 45,         # Q
    "client.controls.gdx.gamemenu": 41,    # M
    "client.controls.gdx.codex": 42,       # N  Pokedex
    "client.controls.gdx.friendlist": 50,  # V
    "client.controls.gdx.incubator": 37,   # I
    "client.controls.gdx.team": 35,        # G
    "client.controls.gdx.tradelink": 44,   # P  GTL
    "client.controls.gdx.trainer": 31,     # C
    "client.controls.gdx.next": 93,        # Page Down
    "client.controls.gdx.previous": 92,    # Page Up
    "client.controls.gdx.screenshot": 141, # F11
    "client.controls.gdx.hidegui": 142,    # F12
    **{f"client.controls.gdx.hotbar{i}": 7 + i for i in range(1, 10)},  # 1-9
    "client.input.controllers.enable_native_support": "false",
}


def backup(p: Path):
    b = p.with_name(p.name + ".bak-pokemmo-controller")
    if p.exists() and not b.exists():
        shutil.copy2(p, b)


def patch_properties(path: Path):
    backup(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        k = line.split("=", 1)[0]
        if k in GAME_BINDS:
            lines[i] = f"{k}={GAME_BINDS[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in GAME_BINDS.items() if k not in seen]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"patched {path}")


# ---- binary VDF (shortcuts.vdf) ----
def _cstr(b, i):
    j = b.index(b"\0", i)
    return b[i:j].decode("utf-8", "replace"), j + 1


def parse_bvdf(b, i=0):
    d = {}
    while True:
        t = b[i]; i += 1
        if t == 8:
            return d, i
        k, i = _cstr(b, i)
        if t == 0:
            d[k], i = parse_bvdf(b, i)
        elif t == 1:
            d[k], i = _cstr(b, i)
        elif t == 2:
            d[k] = struct.unpack_from("<i", b, i)[0]; i += 4
        else:
            raise ValueError(f"unknown type {t}")


def dump_bvdf(d):
    out = b""
    for k, v in d.items():
        kb = k.encode() + b"\0"
        if isinstance(v, dict):
            out += b"\0" + kb + dump_bvdf(v)
        elif isinstance(v, int):
            out += b"\2" + kb + struct.pack("<i", v)
        else:
            out += b"\1" + kb + str(v).encode() + b"\0"
    return out + b"\x08"


def add_shortcut(userdir: Path, exe: Path):
    p = userdir / "config" / "shortcuts.vdf"
    data = {"shortcuts": {}}
    if p.exists():
        backup(p)
        data, _ = parse_bvdf(p.read_bytes())
    sc = data.setdefault("shortcuts", {})
    for v in sc.values():
        if v.get("AppName", v.get("appname")) == SHORTCUT_NAME:
            print("Steam shortcut already present")
            return v["appid"]
    exe_q = f'"{exe}"'
    appid_u = (binascii.crc32((exe_q + SHORTCUT_NAME).encode()) & 0xFFFFFFFF) | 0x80000000
    appid = struct.unpack("<i", struct.pack("<I", appid_u))[0]
    sc[str(len(sc))] = {
        "appid": appid, "AppName": SHORTCUT_NAME, "Exe": exe_q,
        "StartDir": f'"{exe.parent}\\"', "icon": str(exe), "ShortcutPath": "",
        "LaunchOptions": "", "IsHidden": 0, "AllowDesktopConfig": 1, "AllowOverlay": 1,
        "OpenVR": 0, "Devkit": 0, "DevkitGameID": "", "DevkitOverrideAppID": 0,
        "LastPlayTime": 0, "FlatpakAppID": "", "sortas": "", "tags": {},
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\0shortcuts\0" + dump_bvdf(sc) + b"\x08")
    print(f"added Steam shortcut {SHORTCUT_NAME} (appid {appid_u})")
    return appid


def install_layout(steam: Path, account: str):
    for ctype in ("controller_xboxone", "controller_xbox360"):
        install_one(steam, account, ctype)


def install_one(steam: Path, account: str, ctype: str):
    cfg = steam / "steamapps" / "common" / "Steam Controller Configs" / account / "config"
    d = cfg / CONFIG_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{ctype}.vdf"
    backup(dst)
    shutil.copy2(LAYOUT.with_name(f"{ctype}.vdf"), dst)
    cs = cfg / f"configset_{ctype}.vdf"
    txt = cs.read_text(encoding="utf-8") if cs.exists() else '"controller_config"\n{\n}\n'
    backup(cs)
    entry = f'\t"{CONFIG_DIR_NAME}"\n\t{{\n\t\t"autosave"\t\t"1"\n\t}}\n'
    pat = re.compile(r'\t"' + CONFIG_DIR_NAME + r'"\n\t\{.*?\n\t\}\n', re.S)
    txt = pat.sub("", txt)
    txt = txt.rstrip()
    assert txt.endswith("}")
    txt = txt[:-1] + entry + "}\n"
    cs.write_text(txt, encoding="utf-8")
    print(f"installed layout to {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokemmo", default=r"C:\Program Files\PokeMMO")
    ap.add_argument("--steam", default=r"C:\Program Files (x86)\Steam")
    a = ap.parse_args()
    pm, steam = Path(a.pokemmo), Path(a.steam)
    patch_properties(pm / "config" / "main.properties")
    users = [u for u in (steam / "userdata").iterdir() if u.name.isdigit() and u.name != "0"]
    for u in users:
        add_shortcut(u, pm / "PokeMMO.exe")
        install_layout(steam, u.name)
    print("Done. Start Steam, then launch PokeMMO from your Steam library.")


if __name__ == "__main__":
    sys.exit(main())
