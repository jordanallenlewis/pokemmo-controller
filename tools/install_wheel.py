"""Add a labeled right-stick wheel to the native PokeMMO layout (Steam Input).

Every button, the left stick, D-pad and triggers pass straight through to
PokeMMO's own controller binds (tools/apply_native.py). Only the right stick
changes: tilting it shows a labeled Steam radial menu; releasing on a slice
presses that one key. One input -> one key, per PokeMMO's macro policy.

Close PokeMMO and Steam, then:  python tools/install_wheel.py
Then launch PokeMMO from the Steam library (shortcut "PokeMMO").
Backs up every file it touches as *.bak-pokemmo-controller.
"""
import argparse, binascii, re, shutil, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "steam"
SHORTCUT_NAME = "PokeMMO"
CONFIG_DIR_NAME = "pokemmo"

# Wheel slices, clockwise from the top: (Steam key, label). Keys must match
# PokeMMO's keyboard binds (set below in KEYBOARD_BINDS).
WHEEL = [
    ("N", "Pokedex"), ("I", "Egg Incubators"), ("C", "Trainer Card"),
    ("V", "Friends"), ("P", "Global Trade Link"), ("6", "Hotbar 6"),
    ("7", "Hotbar 7"), ("8", "Hotbar 8"), ("9", "Hotbar 9"), ("F12", "Hide GUI"),
]
# libGDX key codes PokeMMO stores in main.properties
KEYBOARD_BINDS = {
    "client.controls.gdx.codex": 42, "client.controls.gdx.incubator": 37,
    "client.controls.gdx.trainer": 31, "client.controls.gdx.friendlist": 50,
    "client.controls.gdx.tradelink": 44, "client.controls.gdx.hidegui": 142,
    "client.controls.gdx.hotbar6": 13, "client.controls.gdx.hotbar7": 14,
    "client.controls.gdx.hotbar8": 15, "client.controls.gdx.hotbar9": 16,
}


# ---------------------------------------------------------------- layout file
def _input(name, binding):
    return (f'\t\t\t"{name}"\n\t\t\t{{\n\t\t\t\t"activators"\n\t\t\t\t{{\n'
            f'\t\t\t\t\t"Full_Press"\n\t\t\t\t\t{{\n\t\t\t\t\t\t"bindings"\n\t\t\t\t\t\t{{\n'
            f'\t\t\t\t\t\t\t"binding"\t\t"{binding}"\n'
            f'\t\t\t\t\t\t}}\n\t\t\t\t\t}}\n\t\t\t\t}}\n\t\t\t}}\n')


def _group(gid, mode, inputs, settings=None):
    s = f'\t"group"\n\t{{\n\t\t"id"\t\t"{gid}"\n\t\t"mode"\t\t"{mode}"\n\t\t"inputs"\n\t\t{{\n'
    s += "".join(_input(n, b) for n, b in inputs)
    s += "\t\t}\n"
    if settings:
        s += "\t\t\"settings\"\n\t\t{\n"
        s += "".join(f'\t\t\t"{k}"\t\t"{v}"\n' for k, v in settings.items())
        s += "\t\t}\n"
    return s + "\t}\n"


def build_layout(controller_type):
    x = lambda b: f"xinput_button {b}"
    g = ""
    g += _group(0, "four_buttons", [("button_a", x("A")), ("button_b", x("B")),
                                     ("button_x", x("X")), ("button_y", x("Y"))])
    g += _group(1, "dpad", [("dpad_north", x("DPAD_UP")), ("dpad_south", x("DPAD_DOWN")),
                            ("dpad_east", x("DPAD_RIGHT")), ("dpad_west", x("DPAD_LEFT"))],
                {"requires_click": "0"})
    g += _group(2, "joystick_move", [("click", x("JOYSTICK_LEFT"))])
    g += _group(3, "radial_menu",
                [(f"touch_menu_button_{i}", f"key_press {k}, {label}, , ")
                 for i, (k, label) in enumerate(WHEEL)] + [("click", x("JOYSTICK_RIGHT"))],
                {"touch_menu_button_count": str(len(WHEEL)),
                 "touchmenu_button_fire_type": "2",  # fire on release
                 "touch_menu_show_labels": "1"})
    g += _group(4, "trigger", [("click", x("TRIGGER_LEFT"))], {"output_trigger": "1"})
    g += _group(5, "trigger", [("click", x("TRIGGER_RIGHT"))], {"output_trigger": "2"})
    g += _group(6, "switches", [("button_escape", x("START")), ("button_menu", x("SELECT")),
                                ("left_bumper", x("SHOULDER_LEFT")),
                                ("right_bumper", x("SHOULDER_RIGHT"))])
    return f'''"controller_mappings"
{{
\t"version"\t\t"3"
\t"revision"\t\t"1"
\t"title"\t\t"PokeMMO - native + right-stick wheel"
\t"description"\t\t"All buttons pass through to PokeMMO's own controller binds. Right stick opens a labeled wheel: Pokedex, Incubators, Trainer, Friends, GTL, Hotbar 6-9, Hide GUI."
\t"creator"\t\t"0"
\t"progenitor"\t\t""
\t"url"\t\t""
\t"export_type"\t\t"personal_local"
\t"controller_type"\t\t"{controller_type}"
\t"major_revision"\t\t"0"
\t"minor_revision"\t\t"0"
\t"Timestamp"\t\t"0"
\t"actions"
\t{{
\t\t"Default"
\t\t{{
\t\t\t"title"\t\t"Default"
\t\t\t"legacy_set"\t\t"1"
\t\t}}
\t}}
\t"action_layers"
\t{{
\t}}
\t"localization"
\t{{
\t}}
{g}\t"preset"
\t{{
\t\t"id"\t\t"0"
\t\t"name"\t\t"Default"
\t\t"group_source_bindings"
\t\t{{
\t\t\t"0"\t\t"button_diamond active"
\t\t\t"1"\t\t"dpad active"
\t\t\t"2"\t\t"joystick active"
\t\t\t"3"\t\t"right_joystick active"
\t\t\t"4"\t\t"left_trigger active"
\t\t\t"5"\t\t"right_trigger active"
\t\t\t"6"\t\t"switch active"
\t\t}}
\t}}
\t"settings"
\t{{
\t}}
}}
'''


# ---------------------------------------------------------------- helpers
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
        if k in KEYBOARD_BINDS:
            lines[i] = f"{k}={KEYBOARD_BINDS[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in KEYBOARD_BINDS.items() if k not in seen]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    if any(v.get("AppName", v.get("appname")) == SHORTCUT_NAME for v in sc.values()):
        return
    exe_q = f'"{exe}"'
    appid_u = (binascii.crc32((exe_q + SHORTCUT_NAME).encode()) & 0xFFFFFFFF) | 0x80000000
    sc[str(len(sc))] = {
        "appid": struct.unpack("<i", struct.pack("<I", appid_u))[0], "AppName": SHORTCUT_NAME,
        "Exe": exe_q, "StartDir": f'"{exe.parent}\\"', "icon": str(exe), "ShortcutPath": "",
        "LaunchOptions": "", "IsHidden": 0, "AllowDesktopConfig": 1, "AllowOverlay": 1,
        "OpenVR": 0, "Devkit": 0, "DevkitGameID": "", "DevkitOverrideAppID": 0,
        "LastPlayTime": 0, "FlatpakAppID": "", "sortas": "", "tags": {},
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\0shortcuts\0" + dump_bvdf(sc) + b"\x08")
    print(f"added Steam shortcut {SHORTCUT_NAME} (appid {appid_u})")


def install_layout(steam: Path, account: str, ctype: str, text: str):
    cfg = steam / "steamapps" / "common" / "Steam Controller Configs" / account / "config"
    d = cfg / CONFIG_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ctype}.vdf").write_text(text, encoding="utf-8", newline="\n")
    cs = cfg / f"configset_{ctype}.vdf"
    txt = cs.read_text(encoding="utf-8") if cs.exists() else '"controller_config"\n{\n}\n'
    backup(cs)
    txt = re.sub(r'\t"' + CONFIG_DIR_NAME + r'"\n\t\{.*?\n\t\}\n', "", txt, flags=re.S).rstrip()
    txt = txt[:-1] + f'\t"{CONFIG_DIR_NAME}"\n\t{{\n\t\t"autosave"\t\t"1"\n\t}}\n}}\n'
    cs.write_text(txt, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokemmo", default=r"C:\Program Files\PokeMMO")
    ap.add_argument("--steam", default=r"C:\Program Files (x86)\Steam")
    ap.add_argument("--build-only", action="store_true", help="only write steam/*.vdf")
    a = ap.parse_args()
    layouts = {t: build_layout(t) for t in ("controller_xboxone", "controller_xbox360")}
    OUT_DIR.mkdir(exist_ok=True)
    for t, text in layouts.items():
        (OUT_DIR / f"{t}.vdf").write_text(text, encoding="utf-8", newline="\n")
    if a.build_only:
        return
    pm, steam = Path(a.pokemmo), Path(a.steam)
    patch_properties(pm / "config" / "main.properties")
    for u in (steam / "userdata").iterdir():
        if u.name.isdigit() and u.name != "0":
            add_shortcut(u, pm / "PokeMMO.exe")
            for t, text in layouts.items():
                install_layout(steam, u.name, t, text)
    print("Done. Start Steam and launch PokeMMO from the Steam library.")


if __name__ == "__main__":
    main()
