"""Write the PokeMMO controller binds into config/main.properties.

Works on Windows, macOS and Linux, for Xbox, PlayStation (DualShock 4 /
DualSense) and Nintendo Switch Pro controllers. These are PokeMMO's own
controller binds (Settings -> Controls); the right stick is left unbound for
the optional Steam wheel (install_wheel.py).

Close PokeMMO first (it rewrites main.properties on exit), then run:
    python tools/apply_native.py [--pokemmo <data folder>]
Backs up main.properties once as main.properties.bak-pokemmo-controller.

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
import argparse, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
    "KEY_RING_FOCUS": B(4),      # View/Share/Minus: Focus Ring, reaches every hotbar slot, party, windows
    "KEY_GAMEMENU": B(6),        # Menu/Options/Plus: Game Menu (Party, Pokedex, Settings...)
    "KEY_INVENTORY": B(10),      # RB/R1/R: Bag
    "KEY_NEXT": AX(5, True),     # RT/R2/ZR: next hotbar page
    "KEY_PREVIOUS": AX(4, True), # LT/L2/ZL: previous hotbar page
    # hotbar
    "KEY_HOTBAR_1": B(11), "KEY_HOTBAR_2": B(14), "KEY_HOTBAR_3": B(12), "KEY_HOTBAR_4": B(13),
    "KEY_HOTBAR_5": B(9),        # LB/L1/L
    # right stick: left free for the Steam wheel (tools/install_wheel.py)
    "KEY_TEAM": B(7),            # L3: Team
    "KEY_SCREENSHOT": B(8),      # R3: Screenshot
}
# On Nintendo pads the printed A is on the right. By default confirm follows the
# label (A confirms, B cancels, like on a Switch); --switch-positional keeps
# confirm on the bottom button like Xbox/PlayStation.
NINTENDO_LABELS = {"KEY_A": B(1), "KEY_B": B(0), "KEY_X": B(3), "KEY_Y": B(2)}

MAP_KEY = "client.controls.controller_input_maps_gdx_2"
LOG_LINE = re.compile(r"Controller (.+?) \( ax \d+ btn \d+\) .*attached")


def unescape(v):  # java.util.Properties escapes
    return re.sub(r"\\(.)", r"\1", v)


def escape_name(n):
    return n.replace("\\", "\\\\").replace("#", "\\#").replace("!", "\\!").replace(":", "\\:").replace("=", "\\=")


def is_nintendo(name):
    return "nintendo" in name.lower() or name == "Pro Controller"


def encode_one(name, nintendo_labels=True):
    layout = dict(LAYOUT)
    if nintendo_labels and is_nintendo(name):
        layout.update(NINTENDO_LABELS)
    parts = [escape_name(name)]
    for action, spec in layout.items():
        if spec[0] == "BUTTON":
            parts.append(f"{action},BUTTON,{spec[1]}")
        else:
            parts.append(f"{action},AXIS,{spec[1]},{'true' if spec[2] else 'false'}")
    return ";".join(parts)


def logged_names(pokemmo: Path):
    """Pad names PokeMMO has logged as attached on this machine."""
    names = []
    for f in (pokemmo / "log").glob("*.log"):
        try:
            for m in LOG_LINE.finditer(f.read_text(encoding="utf-8", errors="replace")):
                if m.group(1) not in names:
                    names.append(m.group(1))
        except OSError:
            pass
    return names


def split_entries(value):
    """Existing map value -> {controller name: raw entry}, unescaped names."""
    out = {}
    for entry in re.split(r"(?<!\\)\|", value) if value else []:
        name = unescape(entry.split(";", 1)[0])
        if name:
            out[name] = entry
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    ap.add_argument("--name", action="append", default=[],
                    help="extra controller name to bind (as shown in PokeMMO Settings); repeatable")
    ap.add_argument("--switch-positional", action="store_true",
                    help="Nintendo pads: confirm on the bottom button (B) like Xbox, not the printed A")
    a = ap.parse_args()
    require_closed()
    pm = find_pokemmo(a.pokemmo)
    p = pm / "config" / "main.properties"
    bak = p.with_name(p.name + ".bak-pokemmo-controller")
    if not bak.exists():
        shutil.copy2(p, bak)

    lines = p.read_text(encoding="utf-8").splitlines()
    old = next((l.split("=", 1)[1] for l in lines if l.split("=", 1)[0] == MAP_KEY), "")
    seen_here = logged_names(pm)
    names = list(dict.fromkeys(CONTROLLER_NAMES + a.name + seen_here))
    entries = split_entries(old)  # keep maps for other pads the player bound by hand
    for n in names:
        entries[n] = encode_one(n, not a.switch_positional)
    want = {MAP_KEY: "|".join(entries.values()),
            "client.input.controllers.enable_native_support": "true"}
    seen = set()
    for i, line in enumerate(lines):
        k = line.split("=", 1)[0]
        if k in want:
            lines[i] = f"{k}={want[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in want.items() if k not in seen]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote controller layout for {len(names)} controller names to {p}")
    new = [n for n in seen_here if n not in CONTROLLER_NAMES]
    if new:
        print("  including pads PokeMMO logged here:", ", ".join(new))


if __name__ == "__main__":
    main()
