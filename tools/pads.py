"""What each controller input is printed as on Xbox, PlayStation and Switch Pro pads
(the names are defined in layout.py; the pictures are rendered from real photos, see docs/art/).

SDL3 (which PokeMMO reads pads through) numbers inputs by position, so one layout
fits every pad; this file only supplies the names a player sees. Nothing here
changes what is written to the game or to Steam: it reads a layout and describes it.

    python tools/pads.py [xbox|playstation|switch]     print the layout for that pad
    python tools/pads.py switch --switch-positional    ... with the bottom button confirming

Switch Pro pads print A on the right. By default the installer follows the printed
letters (the face buttons swap in pairs, layout.NINTENDO_LABEL_SWAP), so the names
here do too; switch_positional=True names them as --switch-positional installs them.

Standard library only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

FAMILIES = ("xbox", "playstation", "switch")
TITLES = {f: L.PADS[f]["title"] for f in FAMILIES}

NOT_BOUND = "Not bound"

# The names themselves live in layout.py (PADS); these are thin wrappers kept for the callers.
physical_button = L.physical_button
button_label = L.button_label
axis_label = L.axis_label


def input_label(family, spec, switch_positional=False):
    if spec is None:
        return NOT_BOUND
    if "button" in spec:
        return button_label(family, spec["button"], switch_positional)
    return axis_label(family, spec["axis"], spec.get("positive", True))


def describe(lay, family, switch_positional=False):
    """[(action id, action name, printed input)] in the order of L.ACTIONS ("Not bound" if none)."""
    return [(a, L.ACTIONS[a], input_label(family, lay["binds"].get(a), switch_positional)) for a in L.ACTIONS]


def main(argv):
    positional = "--switch-positional" in argv
    rest = [x for x in argv if x != "--switch-positional"]
    fam = rest[0] if rest else "xbox"
    if fam not in FAMILIES or len(rest) > 1:
        print(f"usage: pads.py [{'|'.join(FAMILIES)}] [--switch-positional]", file=sys.stderr)
        return 2
    print(f"{TITLES[fam]} pad, default layout"
          + (", --switch-positional" if positional and fam == "switch" else ""))
    for a, name, inp in describe(L.default_layout(), fam, positional):
        print(f"  {inp:<18} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
