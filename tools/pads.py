"""What each controller input is printed as on Xbox, PlayStation and Switch Pro pads,
and the button-map pictures built from a layout.

SDL3 (which PokeMMO reads pads through) numbers inputs by position, so one layout
fits every pad; this file only supplies the names a player sees. Nothing here
changes what is written to the game or to Steam: it reads a layout and describes it.

    python tools/pads.py [xbox|playstation|switch]     print the layout for that pad
    python tools/pads.py switch --switch-positional    ... with the bottom button confirming
    python tools/pads.py --art                         rewrite docs/button-map-*.svg

Switch Pro pads print A on the right. By default the installer follows the printed
letters (the face buttons swap in pairs, layout.NINTENDO_LABEL_SWAP), so the names
here do too; switch_positional=True names them as --switch-positional installs them.

Standard library only.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

FAMILIES = ("xbox", "playstation", "switch")
TITLES = {"xbox": "Xbox", "playstation": "PlayStation", "switch": "Switch Pro"}

NOT_BOUND = "Not bound"

# index (SDL3 position, the physical button) -> printed name
_BUTTONS = {
    "xbox": ["A", "B", "X", "Y", "View", "Xbox", "Menu", "L3", "R3", "LB", "RB",
             "D-pad up", "D-pad down", "D-pad left", "D-pad right"],
    "playstation": ["Cross", "Circle", "Square", "Triangle", "Create", "PS", "Options", "L3", "R3",
                    "L1", "R1", "D-pad up", "D-pad down", "D-pad left", "D-pad right"],
    # a Switch pad prints its bottom button B and its right button A
    "switch": ["B", "A", "Y", "X", "Minus", "Home", "Plus", "L3", "R3", "L", "R",
               "D-pad up", "D-pad down", "D-pad left", "D-pad right"],
}
_AXES = {
    "xbox": ["Left stick", "Left stick", "Right stick", "Right stick", "LT", "RT"],
    "playstation": ["Left stick", "Left stick", "Right stick", "Right stick", "L2", "R2"],
    "switch": ["Left stick", "Left stick", "Right stick", "Right stick", "ZL", "ZR"],
}
_STICK_DIR = {0: ("left", "right"), 1: ("up", "down"), 2: ("left", "right"), 3: ("up", "down")}


def physical_button(family, n, switch_positional=False):
    """The physical button (SDL3 position) a layout's button n ends up on for this pad."""
    if family == "switch" and not switch_positional:
        return L.NINTENDO_LABEL_SWAP.get(n, n)
    return n


def button_label(family, n, switch_positional=False):
    """What is printed on the button that does layout button n's action on this pad."""
    return _BUTTONS[family][physical_button(family, n, switch_positional)]


def axis_label(family, axis, positive):
    name = _AXES[family][axis]
    if axis in _STICK_DIR:
        return f"{name} {_STICK_DIR[axis][1 if positive else 0]}"
    return name


def input_label(family, spec, switch_positional=False):
    if spec is None:
        return NOT_BOUND
    if "button" in spec:
        return button_label(family, spec["button"], switch_positional)
    return axis_label(family, spec["axis"], spec.get("positive", True))


def describe(lay, family, switch_positional=False):
    """[(action id, action name, printed input)] in the order of L.ACTIONS ("Not bound" if none)."""
    return [(a, L.ACTIONS[a], input_label(family, lay["binds"].get(a), switch_positional)) for a in L.ACTIONS]


# ---------------------------------------------------------------- the picture
# Plain vector pad outline (no photo, so no licence to carry) with a call-out per input.
_W, _H = 1800, 990
# anchor points on the outline for each input: name -> (x, y, side)
_SPOTS = {
    ("axis", 4): (600, 250, "L"), ("button", 9): (650, 285, "L"), ("button", 4): (860, 390, "L"),
    ("button", 7): (640, 390, "L"), ("button", 11): (760, 480, "L"), ("button", 13): (725, 520, "L"),
    ("button", 14): (795, 520, "L"), ("button", 12): (760, 560, "L"),
    ("axis", 5): (1200, 250, "R"), ("button", 10): (1150, 285, "R"), ("button", 6): (1000, 390, "R"),
    ("button", 3): (1240, 350, "R"), ("button", 1): (1290, 390, "R"), ("button", 2): (1190, 390, "R"),
    ("button", 0): (1240, 430, "R"), ("button", 8): (1000, 520, "R"), ("button", 5): (930, 330, "R"),
}


def _spot_for(spec, family, switch_positional=False):
    if spec is None:
        return None
    if "button" in spec:
        return _SPOTS.get(("button", physical_button(family, spec["button"], switch_positional)))
    return _SPOTS.get(("axis", spec["axis"]))


def _subtitle(family, switch_positional):
    if family != "switch":
        return f"{TITLES[family]} names. Same spots as Xbox; one input does one action."
    if switch_positional:
        return "Switch Pro names, --switch-positional: the bottom button confirms, like Xbox. One input does one action."
    return "Switch Pro names: the printed A confirms, like on a Switch. One input does one action."


def render_svg(lay, family, switch_positional=False):
    L.validate(lay)
    t = TITLES[family]
    rows = []
    for a in L.ACTIONS:
        spec = lay["binds"].get(a)
        rows.append((a, L.ACTIONS[a], input_label(family, spec, switch_positional),
                     _spot_for(spec, family, switch_positional)))
    left = [r for r in rows if r[3] and r[3][2] == "L"]
    right = [r for r in rows if r[3] and r[3][2] == "R"]
    other = [r for r in rows if not r[3] and r[2] != NOT_BOUND]  # left stick directions: listed in a box
    unbound = [r[1] for r in rows if r[2] == NOT_BOUND]
    # the lists under the pad grow with the layout: the picture grows with them
    h = max(_H, 898 + (max(len(other), len(unbound), 1) - 1) * 22 + 26)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {h}" width="{_W}" height="{h}" '
         'font-family="\'Segoe UI\',Inter,system-ui,-apple-system,sans-serif" role="img" '
         f'aria-label="PokeMMO button map for a {t} controller">',
         "  <!-- Generated by tools/pads.py from the layout. Do not edit by hand. -->",
         f'  <rect width="{_W}" height="{h}" fill="#14171c"/>',
         '  <text x="64" y="84" font-size="34" font-weight="700" fill="#f2f3f5">PokeMMO on a controller</text>',
         f'  <text x="64" y="118" font-size="18" fill="#8b919c">{xml_escape(_subtitle(family, switch_positional))}</text>',
         '  <path d="M520 300 Q560 230 700 240 L1100 240 Q1240 230 1280 300 L1400 640 Q1420 720 1350 730 '
         'Q1290 735 1250 680 L1180 600 L620 600 L550 680 Q510 735 450 730 Q380 720 400 640 Z" '
         'fill="#2a2f39" stroke="#4a5262" stroke-width="3"/>']
    for side, items in (("L", left), ("R", right)):
        items.sort(key=lambda r: (r[3][1], r[3][0] if side == "L" else -r[3][0]))
        for i, (a, name, inp, (x, y, _)) in enumerate(items):
            ty = 190 + i * 58
            tx = 392 if side == "L" else 1408
            anchor = "end" if side == "L" else "start"
            o.append(f'  <polyline points="{(tx - 14) if side == "R" else (tx + 14)},{ty - 6} {(tx - 40) if side == "R" else (tx + 40)},{ty - 6} {x},{y}" '
                     'fill="none" stroke="#7d8696" stroke-width="1.8"/>')
            o.append(f'  <circle cx="{x}" cy="{y}" r="6.5" fill="#7dd3fc" stroke="#0c0e12" stroke-width="2.5"/>')
            o.append(f'  <text x="{tx}" y="{ty}" text-anchor="{anchor}" font-size="22" font-weight="700" '
                     f'fill="#f2f3f5">{xml_escape(inp)}</text>')
            o.append(f'  <text x="{tx}" y="{ty + 24}" text-anchor="{anchor}" font-size="17" '
                     f'fill="#a8adb7">{xml_escape(name)}</text>')
    o.append('  <text x="64" y="870" font-size="20" font-weight="700" fill="#f2f3f5">Left stick: walk</text>')
    for i, (a, name, inp, _) in enumerate(other):
        o.append(f'  <text x="64" y="{898 + i * 22}" font-size="17" fill="#a8adb7">{xml_escape(inp)}: {xml_escape(name)}</text>')
    if unbound:
        o.append(f'  <text x="1736" y="870" text-anchor="end" font-size="20" font-weight="700" fill="#f2f3f5">{NOT_BOUND}</text>')
        for i, name in enumerate(unbound):
            o.append(f'  <text x="1736" y="{898 + i * 22}" text-anchor="end" font-size="17" fill="#a8adb7">{xml_escape(name)}</text>')
    o.append('  <text x="900" y="870" text-anchor="middle" font-size="20" font-weight="700" fill="#f2f3f5">'
             'Right stick: the wheel (let go on a slice)</text>')
    slices = " · ".join(f"{label} ({key})" for key, label in L.wheel_slices(lay))
    o.append(f'  <text x="900" y="900" text-anchor="middle" font-size="16" fill="#a8adb7">{xml_escape(slices)}</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def main(argv):
    if argv[:1] == ["--art"]:
        out = Path(__file__).resolve().parent.parent / "docs"
        for fam in ("playstation", "switch"):
            (out / f"button-map-{fam}.svg").write_text(render_svg(L.default_layout(), fam),
                                                        encoding="utf-8", newline="\n")
        print("wrote docs/button-map-playstation.svg and docs/button-map-switch.svg")
        return 0
    positional = "--switch-positional" in argv
    rest = [x for x in argv if x != "--switch-positional"]
    fam = rest[0] if rest else "xbox"
    if fam not in FAMILIES or len(rest) > 1:
        print(f"usage: pads.py [{'|'.join(FAMILIES)}] [--switch-positional] | --art", file=sys.stderr)
        return 2
    print(f"{TITLES[fam]} pad, default layout"
          + (", --switch-positional" if positional and fam == "switch" else ""))
    for a, name, inp in describe(L.default_layout(), fam, positional):
        print(f"  {inp:<18} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
