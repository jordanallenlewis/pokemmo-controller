"""Add a labeled right-stick wheel to the native PokeMMO layout (Steam Input).

Every button, the left stick, D-pad and triggers pass straight through to
PokeMMO's own controller binds (tools/apply_native.py). Only the right stick
changes: tilting it shows a labeled Steam radial menu; releasing on a slice
presses that one key. One input -> one key, per PokeMMO's macro policy.

Works with Steam on Windows, macOS and Linux (Steam Deck too), for Xbox,
PlayStation 4/5, Switch Pro and Steam Deck controls.

Close PokeMMO and Steam, then:  python tools/install_wheel.py
Then launch PokeMMO from the Steam library (shortcut "PokeMMO").
Backs up every file it touches as *.bak-pokemmo-controller. Safe to run again.
"""
import argparse, binascii, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as layout_mod  # noqa: E402
from common import (Plan, backup_path, decode, encode, join_lines, read_bytes,  # noqa: E402
                    set_props, split_lines)
from platforms import find_pokemmo, find_steam, require_closed, shortcut_target  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "steam"
SHORTCUT_NAME = "PokeMMO"
CONFIG_DIR_NAME = "pokemmo"
# Steam Input controller types that get the layout: Xbox One/Series, Xbox 360,
# DualSense, DualShock 4, Switch Pro, Steam Deck, Lenovo Legion Go S.
CONTROLLER_TYPES = ("controller_xboxone", "controller_xbox360", "controller_ps5",
                    "controller_ps4", "controller_switch_pro", "controller_neptune",
                    "controller_legion_go_s")

# Wheel slices, clockwise after the top one: (Steam key, label). The top slice itself is always
# left empty (see build_layout): pointing the stick straight up and letting go sends nothing.
# Keys must match PokeMMO's keyboard binds (set below in KEYBOARD_BINDS).
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


def build_layout(controller_type, wheel=None, scale=None):
    WHEEL_ = WHEEL if wheel is None else wheel
    # slice 1 is the top: no binding, so releasing there does nothing; the actions follow it
    SLICES = [None] + list(WHEEL_)
    x = lambda b: f"xinput_button {b}"
    g = ""
    g += _group(0, "four_buttons", [("button_a", x("A")), ("button_b", x("B")),
                                     ("button_x", x("X")), ("button_y", x("Y"))])
    g += _group(1, "dpad", [("dpad_north", x("DPAD_UP")), ("dpad_south", x("DPAD_DOWN")),
                            ("dpad_east", x("DPAD_RIGHT")), ("dpad_west", x("DPAD_LEFT"))],
                {"requires_click": "0"})
    g += _group(2, "joystick_move", [("click", x("JOYSTICK_LEFT"))])
    g += _group(3, "radial_menu",
                # button 0 is the wheel's center: left empty so releasing in the
                # middle cancels. Slices start at 1, clockwise from the top.
                [(f"touch_menu_button_{i}", f"key_press {s[0]}, {s[1]}, , ")
                 for i, s in enumerate(SLICES, start=1) if s] + [("click", x("JOYSTICK_RIGHT"))],
                {"touch_menu_button_count": str(len(SLICES) + 1),
                 "touchmenu_button_fire_type": "2",  # fire on release
                 "touch_menu_show_labels": "1",
                 "touch_menu_position_x": "50",  # screen center
                 "touch_menu_position_y": "50",
                 "touch_menu_scale": str(layout_mod.WHEEL_SCALE_AT_4K if scale is None else scale),
                 "touch_menu_opacity": "90"})
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
\t"description"\t\t"All buttons pass through to PokeMMO's own controller binds. Right stick opens a labeled wheel (top slice does nothing): Pokedex, Incubators, Trainer, Friends, GTL, Hotbar 6-9, Hide GUI."
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


# ---------------------------------------------------------------- binary VDF (shortcuts.vdf)
class Raw:
    """A binary-VDF value type this tool doesn't edit (float, 64-bit ints...); kept as is."""
    SIZES = {3: 4, 7: 8, 10: 8}

    def __init__(self, t, data):
        self.t, self.data = t, data

    def __eq__(self, o):
        return isinstance(o, Raw) and (self.t, self.data) == (o.t, o.data)


def _cstr(b, i):
    j = b.index(b"\0", i)
    return b[i:j].decode("utf-8", "surrogateescape"), j + 1


def parse_bvdf(b, i=0):
    d = {}
    while True:
        t = b[i]; i += 1
        if t in (8, 11):
            return d, i
        k, i = _cstr(b, i)
        if t == 0:
            d[k], i = parse_bvdf(b, i)
        elif t == 1:
            d[k], i = _cstr(b, i)
        elif t == 2:
            d[k] = struct.unpack_from("<i", b, i)[0]; i += 4
        elif t in Raw.SIZES:
            d[k] = Raw(t, b[i:i + Raw.SIZES[t]]); i += Raw.SIZES[t]
        else:
            raise ValueError(f"unknown type {t}")


def dump_bvdf(d):
    out = b""
    for k, v in d.items():
        kb = k.encode("utf-8", "surrogateescape") + b"\0"
        if isinstance(v, dict):
            out += b"\0" + kb + dump_bvdf(v)
        elif isinstance(v, Raw):
            out += bytes([v.t]) + kb + v.data
        elif isinstance(v, int):
            out += b"\2" + kb + struct.pack("<i", v)
        else:
            out += b"\1" + kb + str(v).encode("utf-8", "surrogateescape") + b"\0"
    return out + b"\x08"


def read_shortcuts(data):
    """shortcuts.vdf bytes -> {index: shortcut}. Raises ValueError if unreadable."""
    try:
        top, end = parse_bvdf(data)
    except (IndexError, ValueError, struct.error) as e:
        raise ValueError(str(e))
    sc = top.get("shortcuts")
    if not isinstance(sc, dict) or dump_bvdf(top) + data[end:] != data:
        raise ValueError("unexpected layout")
    return sc


def write_shortcuts(sc):
    return b"\0shortcuts\0" + dump_bvdf(sc) + b"\x08"


def is_pokemmo_shortcut(v):
    return isinstance(v, dict) and v.get("AppName", v.get("appname")) == SHORTCUT_NAME


# ---------------------------------------------------------------- text VDF (configset_*.vdf)
BLOCK = re.compile(r'^\t"' + CONFIG_DIR_NAME + r'"\n\t\{\n.*?\n?^\t\}\n', re.S | re.M)
OUR_BLOCK = f'\t"{CONFIG_DIR_NAME}"\n\t{{\n\t\t"autosave"\t\t"1"\n\t}}\n'
EMPTY_CONFIGSET = '"controller_config"\n{\n}\n'
LAYOUT_TITLE = "PokeMMO - native + right-stick wheel"


def configset_with_block(text, block):
    text = BLOCK.sub("", text).rstrip()
    if not text.endswith("}"):
        raise ValueError("unexpected layout")
    return text[:-1] + block + "}\n"


# ---------------------------------------------------------------- plan
def props_plan(p, pm: Path):
    path = pm / "config" / "main.properties"
    text, nl = decode(p.current(path))
    lines, final = split_lines(text)
    lines = set_props(lines, {k: str(v) for k, v in KEYBOARD_BINDS.items()})
    p.put(path, encode(join_lines(lines, final), nl))


def userdirs(steam: Path):
    ud = steam / "userdata"
    return sorted(u for u in ud.iterdir() if u.name.isdigit() and u.name != "0") if ud.is_dir() else []


def next_key(sc):
    return str(max([int(k) for k in sc if k.isdigit()] + [-1]) + 1)


def restore_lost_shortcuts(sc, old):
    """Put back shortcuts from the backup that are gone: up to v1.0.0 the PokeMMO
    shortcut could overwrite another one. Returns the names restored."""
    ident = lambda v: (v.get("appid"), v.get("AppName", v.get("appname")), v.get("Exe", v.get("exe")))
    ids = {ident(v) for v in sc.values() if isinstance(v, dict)}
    lost = [(k, v) for k, v in old.items()
            if isinstance(v, dict) and not is_pokemmo_shortcut(v) and ident(v) not in ids]
    for k, v in lost:
        sc[k if k not in sc else next_key(sc)] = v
    if lost:  # keep Steam's numeric order
        items = sorted(sc.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 1 << 30)
        sc.clear()
        sc.update(items)
    return [str(v.get("AppName", v.get("appname"))) for _, v in lost]


def shortcut_plan(p, userdir: Path, pm: Path):
    path = userdir / "config" / "shortcuts.vdf"
    data = p.current(path)
    added = p.state.setdefault("shortcuts_added", [])
    legacy = not p.state.get("version") and not p.fresh  # installed by a version without a record
    bak = read_bytes(backup_path(path))
    try:
        sc = read_shortcuts(data) if data else {}
        old = read_shortcuts(bak) if bak is not None else {}
    except ValueError:
        p.notes.append(f"Could not read {path}; add PokeMMO to Steam by hand (Add a Non-Steam Game).")
        return
    if legacy:
        lost = restore_lost_shortcuts(sc, old)
        if lost:
            p.put(path, write_shortcuts(sc))
            p.notes.append(f"Restored Steam shortcuts an older version overwrote: {', '.join(lost)}")
    if any(is_pokemmo_shortcut(v) for v in sc.values()):
        if legacy and str(path) not in added and not any(is_pokemmo_shortcut(v) for v in old.values()):
            added.append(str(path))  # the older version added it
        return
    exe_q, start_dir, options = shortcut_target(pm)
    appid_u = (binascii.crc32((exe_q + SHORTCUT_NAME).encode()) & 0xFFFFFFFF) | 0x80000000
    key = next_key(sc)
    sc[key] = {
        "appid": struct.unpack("<i", struct.pack("<I", appid_u))[0], "AppName": SHORTCUT_NAME,
        "Exe": exe_q, "StartDir": start_dir, "icon": exe_q.strip('"') if exe_q.endswith('.exe"') else "", "ShortcutPath": "",
        "LaunchOptions": options, "IsHidden": 0, "AllowDesktopConfig": 1, "AllowOverlay": 1,
        "OpenVR": 0, "Devkit": 0, "DevkitGameID": "", "DevkitOverrideAppID": 0,
        "LastPlayTime": 0, "FlatpakAppID": "", "sortas": "", "tags": {},
    }
    p.put(path, write_shortcuts(sc))
    if str(path) not in added:
        added.append(str(path))
    p.notes.append(f"Steam shortcut {SHORTCUT_NAME} (appid {appid_u}) in {path}")


def layout_plan(p, steam: Path, account: str, layouts):
    cfg = steam / "steamapps" / "common" / "Steam Controller Configs" / account / "config"
    for ctype, text in layouts.items():
        f = cfg / CONFIG_DIR_NAME / f"{ctype}.vdf"
        cur = p.current(f)
        # a layout Steam saved for a "PokeMMO" shortcut before is kept as the backup
        p.put(f, encode(text), backup_ok=cur is None or LAYOUT_TITLE.encode() not in cur)
        cs = cfg / f"configset_{ctype}.vdf"
        data = p.current(cs)
        text_cs, nl = decode(data) if data is not None else (EMPTY_CONFIGSET, "\n")
        try:
            new = configset_with_block(text_cs, OUR_BLOCK)
        except ValueError:
            p.notes.append(f"Could not read {cs}; pick the PokeMMO layout in Steam by hand.")
            continue
        p.put(cs, encode(new, nl), backup_ok=OUR_BLOCK not in text_cs)


def wheel_layouts(p):
    """{pad type: layout text} for the layout and game resolution in this install record."""
    from apply_native import custom_layout  # the layout chosen in apply_native.plan (same install record)
    lay = custom_layout(p.state)
    wheel = layout_mod.wheel_slices(lay) if lay else None
    screen = layout_mod.recorded_screen(p.state)
    scale = layout_mod.wheel_scale(*screen) if screen else None
    return {t: build_layout(t, wheel, scale) for t in CONTROLLER_TYPES}, screen, scale


def resize_plan(p, steam: Path):
    """Only the wheel layout files, for the size in the install record (no shortcut, no binds)."""
    layouts, _, _ = wheel_layouts(p)
    for u in userdirs(steam):
        layout_plan(p, steam, u.name, layouts)


def plan(p, pm: Path, steam: Path):
    layouts, screen, scale = wheel_layouts(p)
    props_plan(p, pm)
    for u in userdirs(steam):
        shortcut_plan(p, u, pm)
        layout_plan(p, steam, u.name, layouts)
    p.notes.append(f"Right-stick wheel layouts in {steam}")
    if screen:
        p.notes.append(f"Wheel sized for a {screen[0]}x{screen[1]} game picture (Steam size {scale}).")


def write_repo_layouts():
    """Refresh steam/*.vdf in this repo (for people who import them by hand)."""
    try:
        OUT_DIR.mkdir(exist_ok=True)
        for t in CONTROLLER_TYPES:
            f = OUT_DIR / f"{t}.vdf"
            new = encode(build_layout(t))
            if read_bytes(f) != new:
                f.write_bytes(new)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--steam", help="Steam folder (holds userdata/)")
    ap.add_argument("--build-only", action="store_true", help="only write steam/*.vdf")
    a = ap.parse_args()
    write_repo_layouts()
    if a.build_only:
        return
    require_closed(steam=True)
    pm, steam = find_pokemmo(a.pokemmo), find_steam(a.steam)
    p = Plan(pm)
    plan(p, pm, steam)
    p.commit()
    print("\n".join(p.notes))


if __name__ == "__main__":
    main()
