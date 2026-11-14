"""Build the PokeMMO Xbox Steam Input layout (controller_xboxone.vdf).

Every binding is one controller input -> one key or mouse button, so the
layout follows PokeMMO's macro policy ("1 input = 1 client input").
Run: python tools/build_layout.py  (writes steam/controller_xboxone.vdf)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "steam" / "controller_xboxone.vdf"

KEY = "key_press"
MOUSE = "mouse_button"


def bind(kind, value, label):
    return f"{kind} {value}, {label}, , "


def inputs_block(inputs, ind):
    t = "\t" * ind
    out = []
    for name, (kind, value, label) in inputs.items():
        out += [
            f'{t}"{name}"', f"{t}{{",
            f'{t}\t"activators"', f"{t}\t{{",
            f'{t}\t\t"Full_Press"', f"{t}\t\t{{",
            f'{t}\t\t\t"bindings"', f"{t}\t\t\t{{",
            f'{t}\t\t\t\t"binding"\t\t"{bind(kind, value, label)}"',
            f"{t}\t\t\t}}", f"{t}\t\t}}", f"{t}\t}}", f"{t}}}",
        ]
    return out


def group(gid, mode, inputs, settings=None):
    out = ["\t\"group\"", "\t{", f'\t\t"id"\t\t"{gid}"', f'\t\t"mode"\t\t"{mode}"',
           '\t\t"inputs"', "\t\t{"]
    out += inputs_block(inputs, 3)
    out += ["\t\t}"]
    if settings:
        out += ['\t\t"settings"', "\t\t{"]
        out += [f'\t\t\t"{k}"\t\t"{v}"' for k, v in settings.items()]
        out += ["\t\t}"]
    out += ["\t}"]
    return out


def wasd(label="Move"):
    return {
        "dpad_north": (KEY, "W", label), "dpad_south": (KEY, "S", label),
        "dpad_east": (KEY, "D", label), "dpad_west": (KEY, "A", label),
    }


LAYER = {"layer": "1"}

groups = []
# ---- Base set -------------------------------------------------------------
groups += group(0, "four_buttons", {
    "button_a": (KEY, "E", "A - Confirm / Talk"),
    "button_b": (KEY, "B", "B - Cancel / Back / Run"),
    "button_x": (KEY, "Q", "Bag"),
    "button_y": (KEY, "1", "Hotbar 1"),
})
groups += group(1, "dpad", wasd("Move (d-pad)"), {"requires_click": "0"})
left = wasd("Move (stick)")
left["click"] = ("controller_action", "SHOW_KEYBOARD", "On-screen keyboard")
groups += group(2, "dpad", left)
groups += group(3, "joystick_mouse", {"click": (KEY, "RETURN", "Open chat / send")})
groups += group(4, "trigger", {"click": (MOUSE, "RIGHT", "Right click (context menus)")},
                {"output_trigger": "0"})
groups += group(5, "trigger", {"click": (MOUSE, "LEFT", "Left click")},
                {"output_trigger": "0"})
groups += group(6, "switches", {
    "button_escape": (KEY, "M", "Game Menu (Party, Settings...)"),
    "button_menu": ("xinput_button", "SELECT", "Focus Ring (pick anything: hotbar, party, windows)"),
    "left_bumper": ("controller_action", "hold_layer 2 0 0", "Hold: Shortcuts layer"),
    "right_bumper": (KEY, "PAGE_DOWN", "Next hotbar page"),
})
# ---- Shortcuts layer (hold LB) -----------------------------------------
groups += group(7, "four_buttons", {
    "button_a": (KEY, "6", "Hotbar 6"),
    "button_b": (KEY, "7", "Hotbar 7"),
    "button_x": (KEY, "8", "Hotbar 8"),
    "button_y": (KEY, "9", "Hotbar 9"),
}, LAYER)
groups += group(8, "dpad", {
    "dpad_north": (KEY, "2", "Hotbar 2"), "dpad_east": (KEY, "3", "Hotbar 3"),
    "dpad_south": (KEY, "4", "Hotbar 4"), "dpad_west": (KEY, "5", "Hotbar 5"),
}, {"requires_click": "0", **LAYER})
lyr_left = wasd("Move (stick)")
lyr_left["click"] = (KEY, "V", "Friends list")
groups += group(9, "dpad", lyr_left, LAYER)
groups += group(10, "dpad", {
    "dpad_north": (KEY, "N", "Pokedex"), "dpad_east": (KEY, "I", "Egg incubators"),
    "dpad_south": (KEY, "G", "Team (guild)"), "dpad_west": (KEY, "C", "Trainer card"),
    "click": (KEY, "F12", "Hide GUI"),
}, LAYER)
groups += group(11, "trigger", {"click": (KEY, "X", "Key X")}, {"output_trigger": "0", **LAYER})
groups += group(12, "trigger", {"click": (KEY, "Y", "Key Y")}, {"output_trigger": "0", **LAYER})
groups += group(13, "switches", {
    "button_escape": (KEY, "P", "Global Trade Link"),
    "button_menu": (KEY, "F11", "Screenshot"),
    "right_bumper": (KEY, "PAGE_UP", "Previous hotbar page"),
}, LAYER)

DESC = ("Native-feel PokeMMO layout, keyboard+mouse parity. Stick/d-pad move, A confirm, "
        "B cancel, X Bag, Y Hotbar 1, Start Game Menu, View Focus Ring, RB next hotbar page, "
        "RT/LT left/right click, right stick mouse, R3 chat, L3 keyboard. Hold LB: d-pad Hotbar 2-5, "
        "ABXY Hotbar 6-9, right stick Pokedex/Incubators/Team/Trainer, Start GTL, View Screenshot, "
        "RB previous hotbar page, L3 Friends, R3 Hide GUI, LT/RT Key X/Y. Strictly 1 input = 1 output.")

text = [
    '"controller_mappings"', "{",
    '\t"version"\t\t"3"', '\t"revision"\t\t"1"',
    '\t"title"\t\t"PokeMMO - Xbox (full parity)"',
    f'\t"description"\t\t"{DESC}"',
    '\t"creator"\t\t"0"', '\t"progenitor"\t\t""', '\t"url"\t\t""',
    '\t"export_type"\t\t"personal_local"',
    '\t"controller_type"\t\t"controller_xboxone"',
    '\t"major_revision"\t\t"0"', '\t"minor_revision"\t\t"0"', '\t"Timestamp"\t\t"0"',
    '\t"actions"', "\t{", '\t\t"Default"', "\t\t{", '\t\t\t"title"\t\t"Default"',
    '\t\t\t"legacy_set"\t\t"1"', "\t\t}", "\t}",
    '\t"action_layers"', "\t{", '\t\t"Preset_1000001"', "\t\t{",
    '\t\t\t"title"\t\t"Shortcuts (hold LB)"', '\t\t\t"legacy_set"\t\t"1"',
    '\t\t\t"set_layer"\t\t"1"', '\t\t\t"parent_set_name"\t\t"Default"', "\t\t}", "\t}",
    '\t"localization"', "\t{", "\t}",
]
text += groups
text += [
    '\t"preset"', "\t{", '\t\t"id"\t\t"0"', '\t\t"name"\t\t"Default"',
    '\t\t"group_source_bindings"', "\t\t{",
    '\t\t\t"0"\t\t"button_diamond active"', '\t\t\t"1"\t\t"dpad active"',
    '\t\t\t"2"\t\t"joystick active"', '\t\t\t"3"\t\t"right_joystick active"',
    '\t\t\t"4"\t\t"left_trigger active"', '\t\t\t"5"\t\t"right_trigger active"',
    '\t\t\t"6"\t\t"switch active"', "\t\t}", "\t}",
    '\t"preset"', "\t{", '\t\t"id"\t\t"1"', '\t\t"name"\t\t"Preset_1000001"',
    '\t\t"group_source_bindings"', "\t\t{",
    '\t\t\t"7"\t\t"button_diamond active"', '\t\t\t"8"\t\t"dpad active"',
    '\t\t\t"9"\t\t"joystick active"', '\t\t\t"10"\t\t"right_joystick active"',
    '\t\t\t"11"\t\t"left_trigger active"', '\t\t\t"12"\t\t"right_trigger active"',
    '\t\t\t"13"\t\t"switch active"', "\t\t}", "\t}",
    '\t"settings"', "\t{", "\t}", "}", "",
]
OUT.parent.mkdir(parents=True, exist_ok=True)
body = "\n".join(text)
OUT.write_text(body, encoding="utf-8", newline="\n")
print(f"wrote {OUT}")
# Same layout for Xbox 360 pads
OUT360 = OUT.with_name("controller_xbox360.vdf")
OUT360.write_text(body.replace('"controller_xboxone"', '"controller_xbox360"'),
                  encoding="utf-8", newline="\n")
print(f"wrote {OUT360}")
