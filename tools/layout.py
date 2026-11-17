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
import re

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
    "KEY_HOTBAR_4": "Hotbar 4", "KEY_HOTBAR_5": "Hotbar 5 (Town Map)",
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
# SDL3 reports a trigger from 0 (released) to its maximum (pulled), never below 0, so a
# trigger has one direction: pulled ("positive": true). The other would be a dead bind.
TRIGGERS = (4, 5)

# Nintendo pads print A on the right, B at the bottom, X on top and Y on the left: the
# letters of an Xbox pad on the other button of each pair. Following the printed letters
# swaps whole buttons (never single actions), so each input still does exactly one action.
NINTENDO_LABEL_SWAP = {0: 1, 1: 0, 2: 3, 3: 2}

DEFAULT_BINDS = {
    "KEY_UP": {"axis": 1, "positive": False}, "KEY_DOWN": {"axis": 1, "positive": True},
    "KEY_LEFT": {"axis": 0, "positive": False}, "KEY_RIGHT": {"axis": 0, "positive": True},
    "KEY_A": {"button": 0}, "KEY_B": {"button": 1}, "KEY_X": {"button": 2}, "KEY_Y": {"button": 3},
    "KEY_RING_FOCUS": {"button": 9}, "KEY_GAMEMENU": {"button": 6}, "KEY_INVENTORY": {"button": 10},
    "KEY_NEXT": {"axis": 5, "positive": True}, "KEY_PREVIOUS": {"axis": 4, "positive": True},
    "KEY_HOTBAR_1": {"button": 11}, "KEY_HOTBAR_2": {"button": 14}, "KEY_HOTBAR_3": {"button": 12},
    "KEY_HOTBAR_4": {"button": 13}, "KEY_HOTBAR_5": {"button": 4},
    "KEY_TEAM": {"button": 7}, "KEY_SCREENSHOT": {"button": 8},
}
DEFAULT_WHEEL = list(WHEEL_ACTIONS)


class LayoutError(ValueError):
    """The layout breaks a rule. The message says which and what to do."""


def inputs():
    """Every input a bind may use: each button, each stick direction, each trigger pulled."""
    out = [{"button": n} for n in range(BUTTONS)]
    for a in range(AXES):
        if a not in RIGHT_STICK:
            out += [{"axis": a, "positive": p} for p in ((True,) if a in TRIGGERS else (False, True))]
    return out


def default_layout():
    return {"format": FORMAT, "binds": {k: dict(v) for k, v in DEFAULT_BINDS.items()},
            "wheel": list(DEFAULT_WHEEL)}


# ---------------------------------------------------------------- checks
def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _input_of(action, spec, pushed_triggers=False):
    """spec -> ("BUTTON", n) or ("AXIS", n, positive). Refuses anything but one plain input.
    pushed_triggers: also accept a trigger bound the way it never moves (see recorded())."""
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
    if n in TRIGGERS and not pos and not pushed_triggers:
        raise LayoutError(f"{action}: a trigger (axis {n}) only works pulled, so it needs \"positive\": true. "
                          "Released is its resting position and never sends anything.")
    return ("AXIS", n, pos)


def validate(lay, _pushed_triggers=False):
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
        inp = _input_of(action, spec, _pushed_triggers)
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


# ---------------------------------------------------------------- install records
def _pushed(spec):
    return isinstance(spec, dict) and spec.get("axis") in TRIGGERS and spec.get("positive") is False


def recorded(lay):
    """A layout read back from an install record -> (layout, [actions dropped]).

    Records written before triggers were limited to "pulled" may hold a trigger bound the
    other way, a bind that never fires. Those binds are dropped (the action is left unbound)
    and named so the player can be told; the rest of the layout is kept. Anything else the
    rules refuse raises LayoutError, as validate() does."""
    validate(lay, _pushed_triggers=True)
    dropped = [a for a, spec in lay["binds"].items() if _pushed(spec)]
    if not dropped:
        return lay, []
    fixed = dict(lay, binds={a: spec for a, spec in lay["binds"].items() if a not in dropped})
    validate(fixed)
    return fixed, dropped


def recorded_binds(lay):
    """native_binds() of a recorded layout exactly as an earlier run wrote it (a pushed trigger
    included), so update and uninstall still know those map entries as this project's."""
    validate(lay, _pushed_triggers=True)
    return {a: _input_of(a, lay["binds"][a], True) for a in ACTIONS if a in lay["binds"]}


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


# ---------------------------------------------------------------- wheel size
# Steam draws the wheel in screen pixels, so one fixed size that suits a 4K screen
# runs off a smaller one. The size follows the height of the picture the game draws.
WHEEL_SCALE_AT_4K = 400   # what the wheel always used: right for 2160 pixels of height
REFERENCE_HEIGHT = 2160
MIN_WHEEL_SCALE = 60      # a smaller wheel is too small to read its labels
MIN_SIDE, MAX_SIDE = 320, 16384


def parse_resolution(text):
    """'1920x1080' (also 1920*1080, 1920 x 1080, 1920,1080) -> (1920, 1080). Raises LayoutError."""
    m = re.fullmatch(r"\s*(\d{3,5})\s*[x*X,\u00d7]\s*(\d{3,5})\s*", str(text))
    if not m:
        raise LayoutError(f"{text!r} is not a resolution. Write it like 1920x1080.")
    return check_resolution(int(m.group(1)), int(m.group(2)))


def check_resolution(w, h):
    if isinstance(w, bool) or isinstance(h, bool) or not isinstance(w, int) or not isinstance(h, int):
        raise LayoutError("a resolution is two whole numbers, width and height.")
    if not (MIN_SIDE <= w <= MAX_SIDE and MIN_SIDE <= h <= MAX_SIDE):
        raise LayoutError(f"{w}x{h} is outside {MIN_SIDE} to {MAX_SIDE} pixels a side.")
    return w, h


def wheel_scale(w, h):
    """The wheel's Steam size for a game picture of w x h pixels. The shorter side sets it, so
    ultrawide, 4:3 and tall windows all fit; it never goes above the 4K size."""
    short = min(check_resolution(w, h))
    return max(MIN_WHEEL_SCALE, min(WHEEL_SCALE_AT_4K, round(WHEEL_SCALE_AT_4K * short / REFERENCE_HEIGHT)))


def recorded_screen(state):
    """(w, h) saved in the install record, or None (a record edited by hand is not trusted)."""
    v = state.get("screen")
    try:
        return check_resolution(*v) if isinstance(v, list) and len(v) == 2 else None
    except LayoutError:
        return None


def set_screen(state, screen=None, reset=False):
    """Save (or with reset, forget) the game resolution in the install record."""
    if reset:
        state.pop("screen", None)
    elif screen is not None:
        if wheel_scale(*screen) == WHEEL_SCALE_AT_4K:
            state.pop("screen", None)       # the default size: leave no trace
        else:
            state["screen"] = list(screen)
