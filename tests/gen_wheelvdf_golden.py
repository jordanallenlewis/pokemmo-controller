"""Writes tests/golden/wheelvdf-parity.json: the Steam wheel layout text (tools/install_wheel.py
build_layout) and the configset edit, for several pads, wheels and sizes. The Go helper must write
the same bytes (helper/wheelvdf_test.go). Run with --write after a deliberate change to install_wheel.py;
test_wheelvdf_golden fails when the file is stale."""
import json, sys
from pathlib import Path

import helpers  # noqa: F401
import install_wheel as W
import layout as L

OUT = Path(__file__).resolve().parent / "golden" / "wheelvdf-parity.json"

CONFIGSETS = [
    ("empty set", W.EMPTY_CONFIGSET),
    ("other game present", '"controller_config"\n{\n\t"other"\n\t{\n\t\t"autosave"\t\t"0"\n\t}\n}\n'),
    ("our block already there", '"controller_config"\n{\n\t"pokemmo"\n\t{\n\t\t"autosave"\t\t"0"\n\t}\n}\n'),
    ("our block between others", '"controller_config"\n{\n\t"a"\n\t{\n\t}\n\t"pokemmo"\n\t{\n\t\t"x"\t\t"1"\n\t}\n\t"b"\n\t{\n\t}\n}\n'),
    ("no closing brace", '"controller_config"\n{\n'),
    ("trailing spaces", '"controller_config"\n{\n}  \n\n'),
]


def build():
    d = L.default_layout()
    rev = list(reversed(L.wheel_slices(d)))
    layouts = []
    for ctype in W.CONTROLLER_TYPES:
        layouts.append({"label": f"{ctype} default", "type": ctype, "wheel": None, "scale": None,
                        "text": W.build_layout(ctype)})
    for scale in (60, 133, 200, 400):
        layouts.append({"label": f"xbox scale {scale}", "type": "controller_xboxone", "wheel": None, "scale": scale,
                        "text": W.build_layout("controller_xboxone", None, scale)})
    layouts.append({"label": "reversed wheel", "type": "controller_ps5", "wheel": [list(s) for s in rev], "scale": 150,
                    "text": W.build_layout("controller_ps5", rev, 150)})
    short = [list(s) for s in L.wheel_slices(d)][:3]
    layouts.append({"label": "three slices", "type": "controller_neptune", "wheel": short, "scale": None,
                    "text": W.build_layout("controller_neptune", [tuple(s) for s in short], None)})
    cs = []
    for label, text in CONFIGSETS:
        c = {"label": label, "text": text}
        try:
            c["ok"], c["result"] = True, W.configset_with_block(text, W.OUR_BLOCK)
        except ValueError as e:
            c["ok"], c["result"] = False, str(e)
        cs.append(c)
    return {"our_block": W.OUR_BLOCK, "empty_configset": W.EMPTY_CONFIGSET, "layouts": layouts, "configsets": cs}


def dump():
    return json.dumps(build(), indent=1, ensure_ascii=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_text(dump(), encoding="utf-8", newline="\n")
        print("wrote", OUT)
