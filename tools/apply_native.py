"""Write the PokeMMO controller binds into config/main.properties.

Works on Windows, macOS and Linux, for Xbox, PlayStation (DualShock 4 /
DualSense) and Nintendo Switch Pro controllers. These are PokeMMO's own
controller binds (Settings -> Controls); the right stick is left unbound for
the optional Steam wheel (install_wheel.py).

Close PokeMMO first (it rewrites main.properties on exit), then run:
    python tools/apply_native.py [--pokemmo <data folder>]
Backs up main.properties once as main.properties.bak-pokemmo-controller.
Safe to run again: only the controller entries this tool owns are rewritten.

PokeMMO reads pads through SDL3, which numbers buttons by POSITION, the same on
every controller:
  0 bottom (Xbox A / PS Cross / Switch B)    1 right (B / Circle / A)
  2 left   (X / Square / Y)                  3 top   (Y / Triangle / X)
  4 View / Share-Create / Minus   5 Guide / PS / Home   6 Menu / Options / Plus
  7 L3  8 R3  9 LB/L1/L  10 RB/R1/R  11 D-up  12 D-down  13 D-left  14 D-right
  Axes: 0 left X  1 left Y  2 right X  3 right Y  4 LT/L2/ZL  5 RT/R2/ZR
PokeMMO keeps one map per controller name, so the map is written under every
name SDL3 gives these pads, plus any pad PokeMMO has logged on this machine.
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as layout_mod  # noqa: E402
from common import (MAP_KEY, NATIVE_KEY, Plan, backup_path, decode, encode, escape,  # noqa: E402
                    get_prop, join_lines, read_bytes, set_props, split_lines, unescape)
from platforms import find_pokemmo, require_closed  # noqa: E402

# Names from SDL3's source (controller_list.h and the HIDAPI drivers) and the
# Apple / Linux fallbacks. Steam Input's virtual pad covers the wheel setup.
XBOX = ["Xbox Series X Controller", "Xbox One S Controller", "Xbox One Controller",
        "Xbox One Elite Controller", "Xbox One Elite 2 Controller", "Xbox 360 Controller",
        "Xbox 360 Wireless Controller", "Xbox Wireless Controller", "Xbox Adaptive Controller",
        "XInput Controller", "Microsoft X-Box 360 pad", "Microsoft X-Box One pad"]
PLAYSTATION = ["PS5 Controller", "DualSense Wireless Controller",
               "DualSense Edge Wireless Controller", "PS4 Controller",
               "DUALSHOCK 4 Wireless Controller", "Sony Interactive Entertainment Wireless Controller",
               "Wireless Controller"]
NINTENDO = ["Nintendo Switch Pro Controller", "Pro Controller", "Nintendo Switch 2 Pro Controller"]
STEAM = ["#SettingsController_SteamController", "Steam Virtual Gamepad", "Steam Controller",
         "Steam Deck", "Steam Deck Controller"]
CONTROLLER_NAMES = XBOX + PLAYSTATION + NINTENDO + STEAM

B = lambda n: ("BUTTON", n)
AX = lambda n, positive: ("AXIS", n, positive)

LAYOUT = {
    # movement and confirm/cancel (game defaults)
    "KEY_UP": AX(1, False), "KEY_DOWN": AX(1, True),
    "KEY_LEFT": AX(0, False), "KEY_RIGHT": AX(0, True),
    "KEY_A": B(0), "KEY_B": B(1), "KEY_X": B(2), "KEY_Y": B(3),
    # menus
    "KEY_RING_FOCUS": B(9),      # LB/L1/L: Focus Ring, reaches every hotbar slot, party, windows
    "KEY_GAMEMENU": B(6),        # Menu/Options/Plus: Game Menu (Party, Pokedex, Settings...)
    "KEY_INVENTORY": B(10),      # RB/R1/R: Bag
    "KEY_NEXT": AX(5, True),     # RT/R2/ZR: next hotbar page
    "KEY_PREVIOUS": AX(4, True), # LT/L2/ZL: previous hotbar page
    # hotbar
    "KEY_HOTBAR_1": B(11), "KEY_HOTBAR_2": B(14), "KEY_HOTBAR_3": B(12), "KEY_HOTBAR_4": B(13),
    "KEY_HOTBAR_5": B(4),        # View/Share/Minus: Hotbar 5, kept for the Town Map (always opens the map)
    # right stick: left free for the Steam wheel (tools/install_wheel.py)
    "KEY_TEAM": B(7),            # L3: Team
    "KEY_SCREENSHOT": B(8),      # R3: Screenshot
}
# On Nintendo pads the printed A is on the right. By default confirm follows the
# label (A confirms, B cancels, like on a Switch: the face buttons swap in pairs, see
# layout.NINTENDO_LABEL_SWAP); --switch-positional keeps confirm on the bottom button
# like Xbox/PlayStation.
NINTENDO_LABELS = {"KEY_A": B(1), "KEY_B": B(0), "KEY_X": B(3), "KEY_Y": B(2)}

LOG_LINE = re.compile(r"Controller (.+?) \( ax \d+ btn \d+\) .*attached")


def is_nintendo(name):
    return "nintendo" in name.lower() or name == "Pro Controller"


def _parts(layout):
    out = []
    for action, spec in layout.items():
        if spec[0] == "BUTTON":
            out.append(f"{action},BUTTON,{spec[1]}")
        else:
            out.append(f"{action},AXIS,{spec[1]},{'true' if spec[2] else 'false'}")
    return out


def _nintendo(binds):
    """Nintendo pads, confirm on the printed A: every action on a face button moves to the
    button with the same printed letter. A swap of whole buttons, so no two actions meet."""
    swap = layout_mod.NINTENDO_LABEL_SWAP
    return {a: (B(swap[s[1]]) if s[0] == "BUTTON" and s[1] in swap else s) for a, s in binds.items()}


def _nintendo_face_actions_only(binds):
    """What the first remap-screen code wrote for Nintendo pads: only the four face-button
    actions moved, which could put two actions on one button. Still recognised as this
    project's, so a rerun replaces it and uninstall removes it."""
    swap = layout_mod.NINTENDO_LABEL_SWAP
    out = dict(binds)
    for a in ("KEY_A", "KEY_B", "KEY_X", "KEY_Y"):
        if a in out and out[a][0] == "BUTTON" and out[a][1] in swap:
            out[a] = B(swap[out[a][1]])
    return out


def encode_one(name, nintendo_labels=True, binds=None):
    """The map entry for one pad name. binds: a custom layout's native_binds(); default when None."""
    layout = dict(LAYOUT if binds is None else binds)
    if nintendo_labels and is_nintendo(name):
        layout = _nintendo(layout) if binds is not None else dict(layout, **NINTENDO_LABELS)
    return ";".join([escape(name)] + _parts(layout))


def layout_sets(binds):
    """The forms of a layout this project writes (positional, and labels on Nintendo pads, plus
    the older labels form), as sets of bind parts."""
    return {frozenset(_parts(binds)), frozenset(_parts(_nintendo(binds))),
            frozenset(_parts(_nintendo_face_actions_only(binds)))}


# v1.0.0 to v1.1.1 put the Focus Ring on View and Hotbar 5 on LB. Still recognised as this
# project's, so a rerun replaces it and uninstall removes it.
LEGACY_LAYOUT = dict(LAYOUT, KEY_RING_FOCUS=B(4), KEY_HOTBAR_5=B(9))
OUR_LAYOUTS = layout_sets(LAYOUT) | layout_sets(LEGACY_LAYOUT)


def is_ours(entry, extra=frozenset()):
    """True if a map entry is exactly one of this project's layouts (any order): the default,
    or the player's custom one (extra = layout_sets of it)."""
    return frozenset(p for p in entry.split(";")[1:] if p) in (OUR_LAYOUTS | set(extra))


def custom_layout(state):
    """The player's custom layout saved in the install record, or None for the default."""
    lay = state.get("layout")
    if lay is None:
        return None
    try:
        return layout_mod.recorded(lay)[0]
    except layout_mod.LayoutError:
        return None  # a record edited by hand is not trusted: fall back to the default


def custom_sets(state):
    """The map entries the recorded layout made, as an earlier run wrote them."""
    lay = state.get("layout")
    if lay is None:
        return set()
    try:
        return layout_sets(layout_mod.recorded_binds(lay))
    except layout_mod.LayoutError:
        return set()


def logged_names(pokemmo: Path):
    """Pad names PokeMMO has logged as attached on this machine."""
    names = []
    for f in sorted((pokemmo / "log").glob("*.log")):
        try:
            for m in LOG_LINE.finditer(f.read_text(encoding="utf-8", errors="replace")):
                if m.group(1) not in names:
                    names.append(m.group(1))
        except OSError:
            pass
    return names


def split_entries(value):
    """Map value -> {controller name: raw entry}, in file order."""
    out = {}
    for entry in re.split(r"(?<!\\)\|", value) if value else []:
        name = unescape(entry.split(";", 1)[0])
        if name:
            out[name] = entry
    return out


def props_path(pm: Path):
    return Path(pm) / "config" / "main.properties"


def installed(pm: Path, extra=frozenset()):
    """Our layout is in main.properties (written by any version)."""
    data = read_bytes(props_path(pm))
    if data is None:
        return False
    value = get_prop(split_lines(decode(data)[0])[0], MAP_KEY) or ""
    return any(is_ours(e, extra) for e in split_entries(value).values())


def plan(p: Plan, pm: Path, extra_names=(), switch_positional=None, layout=None, reset_layout=False):
    """Add the binds for every known pad name to the plan. Returns the names.

    layout: a validated layout to install; None keeps the one saved in the install
    record (the default when there is none); reset_layout goes back to the default."""
    path = props_path(pm)
    text, nl = decode(p.current(path))
    lines, final = split_lines(text)
    st = p.state
    old_sets = custom_sets(st)          # what an earlier run of ours may have written
    if reset_layout:
        layout = layout_mod.default_layout()
    if layout is not None:
        layout_mod.validate(layout)
        if layout == layout_mod.default_layout():
            st.pop("layout", None)
        else:
            st["layout"] = layout
    elif st.get("layout") is not None:
        try:
            fixed, dropped = layout_mod.recorded(st["layout"])
        except layout_mod.LayoutError:
            dropped = []
        if dropped:
            st["layout"] = fixed
            names = ", ".join(layout_mod.ACTIONS[a] for a in dropped)
            p.notes.append(f"Your layout had {names} on a trigger pushed away, which never sends anything, "
                           "so it is now not bound. Give it another button in the remap screen.")
    cust = custom_layout(st)
    binds = layout_mod.native_binds(cust) if cust else None
    ours = old_sets | custom_sets(st)
    if switch_positional is None:
        switch_positional = bool(st.get("switch_positional"))
    seen_here = logged_names(pm)
    names = list(dict.fromkeys(CONTROLLER_NAMES + list(st.get("extra_names", [])) + list(extra_names)
                               + seen_here))
    entries = split_entries(get_prop(lines, MAP_KEY) or "")
    bak = read_bytes(backup_path(path))
    bak_entries = split_entries(get_prop(split_lines(decode(bak)[0])[0], MAP_KEY) or "") if bak else {}

    p.fresh = not st.get("version") and not installed(pm, ours)
    if p.fresh:
        bak_entries = {}  # a backup left by an old uninstall is not the current original
    elif not st.get("version") and bak is not None:
        # v1.0.0 replaced the whole map and dropped maps made by hand for other
        # pads: bring those back from the backup.
        for n, e in bak_entries.items():
            if n not in entries and not is_ours(e, ours):
                entries[n] = e
    for n in st.get("names", []):
        # names an older version wrote that this one no longer does
        if n not in names and n in entries and is_ours(entries[n], ours):
            if n in bak_entries:
                entries[n] = bak_entries[n]
            else:
                del entries[n]
    for n in names:
        entries[n] = encode_one(n, not switch_positional, binds)

    lines = set_props(lines, {MAP_KEY: "|".join(entries.values()), NATIVE_KEY: "true"})
    p.put(path, encode(join_lines(lines, final), nl), backup_ok=not installed(pm, ours))
    st["names"] = names
    st["switch_positional"] = bool(switch_positional)
    st["extra_names"] = list(dict.fromkeys(list(st.get("extra_names", [])) + list(extra_names)))
    new = [n for n in seen_here if n not in CONTROLLER_NAMES]
    p.notes.append(f"Controller binds for {len(names)} pad names in {path}"
                   + (f" (including pads PokeMMO logged here: {', '.join(new)})" if new else ""))
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--name", action="append", default=[],
                    help="extra controller name to bind (as shown in PokeMMO Settings); repeatable")
    ap.add_argument("--switch-positional", action="store_true", default=None,
                    help="Nintendo pads: confirm on the bottom button (B) like Xbox, not the printed A")
    ap.add_argument("--switch-labels", dest="switch_positional", action="store_false",
                    help="Nintendo pads: confirm on the printed A (the default)")
    a = ap.parse_args()
    require_closed()
    pm = find_pokemmo(a.pokemmo)
    p = Plan(pm)
    plan(p, pm, a.name, a.switch_positional)
    p.commit()
    print("\n".join(p.notes))


if __name__ == "__main__":
    main()
