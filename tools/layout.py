"""The layout: which controller input does which PokeMMO action.

One model shared by the installers, the command line (remap.py) and the
remap screen (ui.py), so there is exactly one place that decides what a valid
layout is and exactly one set of writers (apply_native.py, install_wheel.py).

The rule PokeMMO sets for remapping is "one input from the player produces no
more than one input to the game", and this file enforces it. A layout holds
only:
  binds  one input (a button, or one direction of an axis) for each action
  wheel  ten right-stick slices, each one action, each action at most once
Nothing else is accepted: no turbo, repeat, sequence, delay, combo, macro,
cursor or script field, no input shared by two actions, no list of actions on
one input. A hand-edited layout file is checked by the same code, so it is
refused too. Standard library only.
"""
import json

FORMAT = 1
MAX_BYTES = 64 * 1024

# Native game actions: id -> what it is called in the UI. The ids are
# PokeMMO's own names in main.properties (client.controls.controller_input_maps_gdx_2).
ACTIONS = {
    "KEY_UP": "Move up", "KEY_DOWN": "Move down", "KEY_LEFT": "Move left", "KEY_RIGHT": "Move right",
    "KEY_A": "Confirm / interact", "KEY_B": "Cancel / run", "KEY_X": "Action X", "KEY_Y": "Action Y",
    "KEY_RING_FOCUS": "Focus Ring", "KEY_GAMEMENU": "Game Menu", "KEY_INVENTORY": "Bag",
    "KEY_NEXT": "Next hotbar page", "KEY_PREVIOUS": "Previous hotbar page",
    "KEY_HOTBAR_1": "Hotbar 1", "KEY_HOTBAR_2": "Hotbar 2", "KEY_HOTBAR_3": "Hotbar 3",
    "KEY_HOTBAR_4": "Hotbar 4", "KEY_HOTBAR_5": "Hotbar 5",
    "KEY_TEAM": "Team", "KEY_SCREENSHOT": "Screenshot",
}

# Wheel actions: id -> (Steam key, label, PokeMMO keyboard bind, its libGDX key code).
# The keyboard bind is what makes the key the wheel presses do this one thing.
WHEEL_ACTIONS = {
    "codex": ("N", "Pokedex", "client.controls.gdx.codex", 42),
    "incubator": ("I", "Egg Incubators", "client.controls.gdx.incubator", 37),
    "trainer": ("C", "Trainer Card", "client.controls.gdx.trainer", 31),
    "friendlist": ("V", "Friends", "client.controls.gdx.friendlist", 50),
    "tradelink": ("P", "Global Trade Link", "client.controls.gdx.tradelink", 44),
    "hotbar6": ("6", "Hotbar 6", "client.controls.gdx.hotbar6", 13),
    "hotbar7": ("7", "Hotbar 7", "client.controls.gdx.hotbar7", 14),
    "hotbar8": ("8", "Hotbar 8", "client.controls.gdx.hotbar8", 15),
    "hotbar9": ("9", "Hotbar 9", "client.controls.gdx.hotbar9", 16),
    "hidegui": ("F12", "Hide GUI", "client.controls.gdx.hidegui", 142),
}
WHEEL_SIZE = len(WHEEL_ACTIONS)

# SDL3 numbers pad inputs by position, the same on Xbox, PlayStation and Switch Pro.
BUTTONS = 15            # 0..14
AXES = 6                # 0 left X, 1 left Y, 2 right X, 3 right Y, 4 left trigger, 5 right trigger
RIGHT_STICK = (2, 3)    # belongs to the wheel

DEFAULT_BINDS = {
    "KEY_UP": {"axis": 1, "positive": False}, "KEY_DOWN": {"axis": 1, "positive": True},
    "KEY_LEFT": {"axis": 0, "positive": False}, "KEY_RIGHT": {"axis": 0, "positive": True},
    "KEY_A": {"button": 0}, "KEY_B": {"button": 1}, "KEY_X": {"button": 2}, "KEY_Y": {"button": 3},
    "KEY_RING_FOCUS": {"button": 4}, "KEY_GAMEMENU": {"button": 6}, "KEY_INVENTORY": {"button": 10},
    "KEY_NEXT": {"axis": 5, "positive": True}, "KEY_PREVIOUS": {"axis": 4, "positive": True},
    "KEY_HOTBAR_1": {"button": 11}, "KEY_HOTBAR_2": {"button": 14}, "KEY_HOTBAR_3": {"button": 12},
    "KEY_HOTBAR_4": {"button": 13}, "KEY_HOTBAR_5": {"button": 9},
    "KEY_TEAM": {"button": 7}, "KEY_SCREENSHOT": {"button": 8},
}
DEFAULT_WHEEL = list(WHEEL_ACTIONS)


class LayoutError(ValueError):
    """The layout breaks a rule. The message says which and what to do."""


def default_layout():
    return {"format": FORMAT, "binds": {k: dict(v) for k, v in DEFAULT_BINDS.items()},
            "wheel": list(DEFAULT_WHEEL)}


# ---------------------------------------------------------------- checks
def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _input_of(action, spec):
    """spec -> ("BUTTON", n) or ("AXIS", n, positive). Refuses anything but one plain input."""
    if not isinstance(spec, dict):
        raise LayoutError(f"{action}: each action takes exactly one input, like {{\"button\": 0}}.")
    fields = set(spec)
    if "button" in fields and "axis" in fields:
        raise LayoutError(f"{action}: exactly one input is needed, not a button and an axis.")
    if "button" in fields:
        extra = fields - {"button"}
        kind = "button"
    elif "axis" in fields:
        extra = fields - {"axis", "positive"}
        kind = "axis"
    else:
        raise LayoutError(f"{action}: exactly one input is needed: a \"button\" or an \"axis\".")
    if extra:
        raise LayoutError(f"{action}: unknown field {sorted(extra)[0]!r}. PokeMMO allows one input to do one "
                          "action, so a bind holds only a button, or an axis with a direction.")
    if kind == "button":
        n = spec["button"]
        if not _is_int(n) or not 0 <= n < BUTTONS:
            raise LayoutError(f"{action}: button must be a whole number from 0 to {BUTTONS - 1}.")
        return ("BUTTON", n)
    n, pos = spec["axis"], spec.get("positive")
    if not _is_int(n) or not 0 <= n < AXES:
        raise LayoutError(f"{action}: axis must be a whole number from 0 to {AXES - 1}.")
    if n in RIGHT_STICK:
        raise LayoutError(f"{action}: the right stick (axes 2 and 3) belongs to the wheel.")
    if not isinstance(pos, bool):
        raise LayoutError(f"{action}: an axis needs \"positive\": true or false (which way it is pushed).")
    return ("AXIS", n, pos)


def validate(lay):
    """Raise LayoutError unless lay is a layout this tool will write. Never changes lay."""
    if not isinstance(lay, dict):
        raise LayoutError("A layout is a JSON object with \"format\", \"binds\" and \"wheel\".")
    extra = set(lay) - {"format", "binds", "wheel", "name"}
    if extra:
        raise LayoutError(f"unknown field {sorted(extra)[0]!r}. A layout holds only binds and the wheel: "
                          "PokeMMO's rule is one input, one action, so there are no macros, turbo, "
                          "repeats, sequences or delays.")
    if lay.get("format") != FORMAT:
        raise LayoutError(f"This layout has format {lay.get('format')!r}; this version reads format {FORMAT}.")
    if "name" in lay and not (isinstance(lay["name"], str) and len(lay["name"]) <= 60):
        raise LayoutError("name must be text of at most 60 characters.")
    binds = lay.get("binds")
    if not isinstance(binds, dict):
        raise LayoutError("\"binds\" must be an object: action -> one input.")
    seen = {}
    for action, spec in binds.items():
        if action not in ACTIONS:
            raise LayoutError(f"unknown action {action!r}.")
        inp = _input_of(action, spec)
        if inp in seen:
            raise LayoutError(f"{action} and {seen[inp]} use the same input. PokeMMO allows one input to do "
                              "one action: give one of them another input.")
        seen[inp] = action
    wheel = lay.get("wheel")
    if not isinstance(wheel, list) or len(wheel) != WHEEL_SIZE:
        raise LayoutError(f"\"wheel\" must list exactly {WHEEL_SIZE} slices.")
    used = set()
    for i, a in enumerate(wheel, start=1):
        if not isinstance(a, str):
            raise LayoutError(f"wheel slice {i}: one action per slice, written as its name.")
        if a not in WHEEL_ACTIONS:
            raise LayoutError(f"wheel slice {i}: unknown action {a!r}.")
        if a in used:
            raise LayoutError(f"wheel slice {i}: {a} is on the wheel more than once; each action goes on it once.")
        used.add(a)


# ---------------------------------------------------------------- views the writers use
def native_binds(lay):
    """{action: ("BUTTON", n) | ("AXIS", n, positive)} in a fixed order (what apply_native writes)."""
    validate(lay)
    return {a: _input_of(a, lay["binds"][a]) for a in ACTIONS if a in lay["binds"]}


def wheel_slices(lay):
    """[(Steam key, label)] clockwise from the top (what install_wheel draws)."""
    validate(lay)
    return [(WHEEL_ACTIONS[a][0], WHEEL_ACTIONS[a][1]) for a in lay["wheel"]]


def keyboard_binds():
    """The PokeMMO keyboard binds that make each wheel key do its one action."""
    return {v[2]: v[3] for v in WHEEL_ACTIONS.values()}


# ---------------------------------------------------------------- files
def _no_duplicates(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise LayoutError(f"{k!r} appears twice in the file.")
        d[k] = v
    return d


def loads(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if len(text) > MAX_BYTES:
        raise LayoutError("This file is too big to be a layout.")
    try:
        lay = json.loads(text, object_pairs_hook=_no_duplicates)
    except (ValueError, RecursionError) as e:
        if isinstance(e, LayoutError):
            raise
        raise LayoutError("This is not a layout file (it is not valid JSON).") from None
    validate(lay)
    return lay


def dumps(lay):
    validate(lay)
    return json.dumps(lay, indent=2) + "\n"
