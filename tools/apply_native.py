"""Write the native PokeMMO controller layout into config/main.properties.

PokeMMO's own controller support only, no Steam Input or remapping software.
Close PokeMMO first (it rewrites main.properties on exit), then run:
    python tools/apply_native.py [--pokemmo "C:\\Program Files\\PokeMMO"]
Backs up main.properties once as main.properties.bak-pokemmo-controller.

Button numbers are SDL GameController indices, the same on every Xbox pad:
  0 A  1 B  2 X  3 Y  4 View  5 Guide  6 Menu/Start  7 L3  8 R3  9 LB  10 RB
  11 D-up  12 D-down  13 D-left  14 D-right
  Axes: 0 left X  1 left Y  2 right X  3 right Y  4 LT  5 RT
"""
import argparse, shutil
from pathlib import Path

# PokeMMO stores one map per controller name; these names cover Xbox pads.
CONTROLLER_NAMES = ["Xbox One S Controller", "Xbox 360 Controller",
                    "Xbox Series X Controller", "Xbox Wireless Controller"]

B = lambda n: ("BUTTON", n)
AX = lambda n, positive: ("AXIS", n, positive)

LAYOUT = {
    # movement and confirm/cancel (game defaults)
    "KEY_UP": AX(1, False), "KEY_DOWN": AX(1, True),
    "KEY_LEFT": AX(0, False), "KEY_RIGHT": AX(0, True),
    "KEY_A": B(0), "KEY_B": B(1), "KEY_X": B(2), "KEY_Y": B(3),
    # menus
    "KEY_RING_FOCUS": B(4),      # View: Focus Ring, reaches every hotbar slot, party, windows
    "KEY_GAMEMENU": B(6),        # Menu/Start: Game Menu (Party, Pokedex, Settings...)
    "KEY_INVENTORY": B(10),      # RB: Bag
    "KEY_NEXT": AX(5, True),     # RT: next hotbar page
    "KEY_PREVIOUS": AX(4, True), # LT: previous hotbar page
    # hotbar
    "KEY_HOTBAR_1": B(11), "KEY_HOTBAR_2": B(14), "KEY_HOTBAR_3": B(12), "KEY_HOTBAR_4": B(13),
    "KEY_HOTBAR_5": B(9),        # LB
    # right stick flicks open windows
    "KEY_MONSTERDEX": AX(3, False),  # up: Pokedex
    "KEY_INCUBATOR": AX(3, True),    # down: Egg incubators
    "KEY_TRAINER": AX(2, False),     # left: Trainer card
    "KEY_FRIENDS_LIST": AX(2, True), # right: Friends list
    "KEY_TEAM": B(7),                # L3: Team
    "KEY_SCREENSHOT": B(8),          # R3: Screenshot
}


def encode_one(name):
    parts = [name]
    for action, spec in LAYOUT.items():
        if spec[0] == "BUTTON":
            parts.append(f"{action},BUTTON,{spec[1]}")
        else:
            parts.append(f"{action},AXIS,{spec[1]},{'true' if spec[2] else 'false'}")
    return ";".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokemmo", default=r"C:\Program Files\PokeMMO")
    a = ap.parse_args()
    p = Path(a.pokemmo) / "config" / "main.properties"
    bak = p.with_name(p.name + ".bak-pokemmo-controller")
    if not bak.exists():
        shutil.copy2(p, bak)
    value = "|".join(encode_one(n) for n in CONTROLLER_NAMES)
    want = {
        "client.controls.controller_input_maps_gdx_2": value,
        "client.input.controllers.enable_native_support": "true",
    }
    lines = p.read_text(encoding="utf-8").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        k = line.split("=", 1)[0]
        if k in want:
            lines[i] = f"{k}={want[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in want.items() if k not in seen]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote native controller layout to {p}")


if __name__ == "__main__":
    main()
