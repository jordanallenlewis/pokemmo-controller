"""Writes site/data/layout.json from tools/layout.py, so the website's button map and
wheel always show the layout the installer really puts on. Standard library only.

    python site/build.py          write the file
    python site/build.py --check  fail if the committed file is out of date (CI)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import layout as L  # noqa: E402
from common import VERSION  # noqa: E402

# SDL3 numbers pad buttons by position, the same on Xbox, PlayStation and Switch Pro.
BUTTON_IDS = {0: "a", 1: "b", 2: "x", 3: "y", 4: "view", 5: "guide", 6: "menu", 7: "ls", 8: "rs",
              9: "lb", 10: "rb", 11: "dup", 12: "ddown", 13: "dleft", 14: "dright"}
AXIS_IDS = {(0, False): "ls", (0, True): "ls", (1, False): "ls", (1, True): "ls", (4, True): "lt", (5, True): "rt"}
NAMES = {
    "xbox": {"a": "A", "b": "B", "x": "X", "y": "Y", "view": "View", "menu": "Menu", "ls": "Left stick",
             "rs": "Right stick", "lb": "LB", "rb": "RB", "lt": "LT", "rt": "RT", "dup": "D-pad up",
             "ddown": "D-pad down", "dleft": "D-pad left", "dright": "D-pad right"},
    "playstation": {"a": "Cross", "b": "Circle", "x": "Square", "y": "Triangle", "view": "Create",
                    "menu": "Options", "ls": "L3 / left stick", "rs": "Right stick", "lb": "L1", "rb": "R1",
                    "lt": "L2", "rt": "R2", "dup": "D-pad up", "ddown": "D-pad down", "dleft": "D-pad left",
                    "dright": "D-pad right"},
    "switch": {"a": "B", "b": "A", "x": "Y", "y": "X", "view": "Minus", "menu": "Plus", "ls": "Left stick",
               "rs": "Right stick", "lb": "L", "rb": "R", "lt": "ZL", "rt": "ZR", "dup": "D-pad up",
               "ddown": "D-pad down", "dleft": "D-pad left", "dright": "D-pad right"},
    "deck": {"a": "A", "b": "B", "x": "X", "y": "Y", "view": "View", "menu": "Menu", "ls": "Left stick",
             "rs": "Right stick", "lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2", "dup": "D-pad up",
             "ddown": "D-pad down", "dleft": "D-pad left", "dright": "D-pad right"},
}
# Movement is four binds on one stick; the site shows it as one "Move" control.
MOVES = {"KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"}


def build():
    lay = L.default_layout()
    controls = {}
    for action, spec in lay["binds"].items():
        if action in MOVES:
            controls["ls"] = "Move"
            continue
        if "button" in spec:
            cid = BUTTON_IDS[spec["button"]]
            if cid in ("ls", "rs"):          # a stick pressed in: its own control, the stick itself moves
                controls[cid + "_click"] = L.ACTIONS[action]
                continue
        else:
            cid = AXIS_IDS[(spec["axis"], bool(spec.get("positive")))]
        controls[cid] = L.ACTIONS[action]
    controls["rs"] = "Action wheel"
    wheel = [{"key": k, "label": lbl} for k, lbl in L.wheel_slices(lay)]
    return {"version": VERSION, "controls": controls, "wheel": wheel, "names": NAMES}


def main():
    out = os.path.join(HERE, "data", "layout.json")
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        cur = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
        if cur != text:
            sys.exit("site/data/layout.json is out of date: run python site/build.py")
        print("site/data/layout.json is up to date")
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", os.path.relpath(out))


if __name__ == "__main__":
    main()
