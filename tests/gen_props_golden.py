"""Writes tests/golden/props-parity.json: what the Python .properties helpers (tools/common.py)
do with a list of inputs. The Go helper must do the same (helper/props_test.go). Run with
--write after a deliberate change to common.py; test_props_golden fails when the file is stale."""
import json, sys
from pathlib import Path

import helpers  # noqa: F401
import common as C

OUT = Path(__file__).resolve().parent / "golden" / "props-parity.json"

TEXTS = [
    "", "a=1\n", "a=1", "a=1\nb=2\n", "# c\na = 1\n!x\nb:2\n", "a=1\na=2\n", "  a  =  1  \n",
    "key with\\ space=v\n", "k\n", "k=\n", "\\u0041b=c\n", "a=1\n\n\nb=2\n", "a=x=y:z\n", "\tt=1\n",
    "client.controls.controller_input_maps_gdx_2=KEY_A\\=0\n", "a=1\r\n".replace("\r", ""),
]
WANTS = [{"a": "9"}, {"a": None}, {"new": "1"}, {"a": "9", "b": None, "c": "3"}, {}, {"k": "v"}]
VALUES = ["", "plain", " lead", "a=b", "a:b", "#h", "!x", "back\\slash", "tab\there", "nl\nx",
          "caf\u00e9", "\u2603", "\U0001F600", "\x01", "trail "]


def dump():
    cases = {"split": [], "keys": [], "get": [], "set": [], "escape": [], "unescape": []}
    for t in TEXTS:
        lines, final = C.split_lines(t)
        cases["split"].append({"text": t, "lines": lines, "final": final, "joined": C.join_lines(lines, final)})
        for ln in lines:
            k = C.line_key(ln)
            cases["keys"].append({"line": ln, "key": k, "value": C.line_value(ln) if k is not None else None})
        for key in ["a", "b", "k", "new", "\u0041b"]:
            cases["get"].append({"text": t, "key": key, "value": C.get_prop(lines, key)})
        for want in WANTS:
            cases["set"].append({"text": t, "want": want, "out": C.join_lines(C.set_props(lines, want), final)})
    for v in VALUES:
        e = C.escape(v)
        cases["escape"].append({"value": v, "escaped": e, "back": C.unescape(e)})
    for raw in ["a\\tb", "\\u00e9", "\\\\", "\\=", "x\\qy", "\\u12", "plain"]:
        try:
            cases["unescape"].append({"raw": raw, "value": C.unescape(raw)})
        except Exception:
            pass
    return json.dumps(cases, indent=1, ensure_ascii=True, sort_keys=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_bytes(dump().encode())
        print("wrote", OUT)
    else:
        print(dump())
