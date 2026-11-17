"""Writes tests/golden/layout-parity.json: what the Python layout core says about a list of
layout texts. The Go helper must say the same (helper/layout_test.go). Run with --write to
refresh the file after a deliberate change to tools/layout.py; the test fails when it is stale."""
import copy, json, sys
from pathlib import Path

import helpers  # noqa: F401
import layout as L

OUT = Path(__file__).resolve().parent / "golden" / "layout-parity.json"


def _bind(lay, action, spec):
    lay = copy.deepcopy(lay)
    lay["binds"][action] = spec
    return json.dumps(lay)


def texts():
    d = L.default_layout()
    t = []
    t.append(("default", L.dumps(d)))
    lay = copy.deepcopy(d); lay["wheel"] = list(reversed(lay["wheel"])); t.append(("wheel reversed", json.dumps(lay)))
    lay = copy.deepcopy(d); del lay["binds"]["KEY_SCREENSHOT"]; t.append(("unbound action", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["name"] = "mine"; t.append(("named", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["name"] = "x" * 61; t.append(("name too long", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["name"] = 5; t.append(("name not text", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["binds"]["KEY_INVENTORY"] = {"button": 4}; lay["binds"]["KEY_HOTBAR_5"] = {"button": 10}
    t.append(("swap buttons", json.dumps(lay)))
    for label, spec in [
        ("shared input", {"button": 0}), ("turbo field", {"button": 5, "turbo": True}),
        ("repeat field", {"button": 5, "repeat": 50}), ("button and axis", {"button": 5, "axis": 0, "positive": True}),
        ("empty spec", {}), ("list spec", [{"button": 5}, {"button": 6}]), ("string spec", "A"),
        ("button 15", {"button": 15}), ("button -1", {"button": -1}), ("button true", {"button": True}),
        ("button float", {"button": 5.0}), ("button text", {"button": "5"}),
        ("right stick", {"axis": 2, "positive": True}), ("axis 6", {"axis": 6, "positive": True}),
        ("axis no direction", {"axis": 0}), ("axis direction text", {"axis": 0, "positive": "yes"}),
        ("trigger released", {"axis": 4, "positive": False}), ("trigger pulled", {"axis": 4, "positive": True}),
        ("stick left", {"axis": 0, "positive": False}), ("none spec", None),
    ]:
        t.append((label, _bind(d, "KEY_TEAM", spec)))
    lay = copy.deepcopy(d); del lay["binds"]["KEY_PREVIOUS"]; lay["binds"]["KEY_TEAM"] = {"axis": 4, "positive": True}
    t.append(("trigger moved", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["binds"]["KEY_FLY"] = {"button": 5}; t.append(("unknown action", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["macro"] = [1, 2]; t.append(("macro field", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["format"] = 2; t.append(("format 2", json.dumps(lay)))
    lay = copy.deepcopy(d); del lay["format"]; t.append(("no format", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["format"] = "1"; t.append(("format text", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["binds"] = []; t.append(("binds list", json.dumps(lay)))
    lay = copy.deepcopy(d); del lay["wheel"]; t.append(("no wheel", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["wheel"] = lay["wheel"][:9]; t.append(("short wheel", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["wheel"][1] = lay["wheel"][0]; t.append(("wheel twice", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["wheel"][1] = "teleport"; t.append(("wheel unknown", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["wheel"][1] = 7; t.append(("wheel number", json.dumps(lay)))
    lay = copy.deepcopy(d); lay["wheel"][1] = ["codex", "trainer"]; t.append(("wheel slice list", json.dumps(lay)))
    t.append(("array", "[1, 2]"))
    t.append(("number", "5"))
    t.append(("null", "null"))
    t.append(("not json", "{nope"))
    t.append(("empty", ""))
    t.append(("duplicate key", '{"format": 1, "format": 1, "binds": {}, "wheel": []}'))
    t.append(("duplicate bind", json.dumps(d).replace('"KEY_UP"', '"KEY_UP": {"button": 1}, "KEY_UP"', 1)))
    t.append(("too big", " " * (L.MAX_BYTES + 1)))
    return t


def build():
    out = []
    for label, text in texts():
        case = {"label": label, "text": text}
        try:
            lay = L.loads(text)
            case["ok"] = True
            case["native"] = [[a] + list(v) for a, v in L.native_binds(lay).items()]
            case["wheel"] = [list(s) for s in L.wheel_slices(lay)]
        except L.LayoutError as e:
            case["ok"] = False
            case["error"] = str(e)
        out.append(case)
    scale = []
    for w, h in [(1920, 1080), (3840, 2160), (2560, 1440), (1280, 720), (800, 600), (320, 320), (7680, 4320), (3440, 1440)]:
        scale.append([w, h, L.wheel_scale(w, h)])
    res = []
    for s in ["1920x1080", " 1920 x 1080 ", "1920*1080", "1920,1080", "1920X1080", "1920\u00d71080", "100x100",
              "99999x1080", "20000x20000", "abc", "", "1920x", "320x320", "16384x16384", "16385x1080", "1920x1080x3"]:
        try:
            res.append([s, True, list(L.parse_resolution(s))])
        except L.LayoutError as e:
            res.append([s, False, str(e)])
    return {"cases": out, "wheel_scale": scale, "resolution": res}


def dump():
    return json.dumps(build(), indent=1, ensure_ascii=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_text(dump(), encoding="utf-8", newline="\n")
        print("wrote", OUT)
