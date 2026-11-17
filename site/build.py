"""Writes every generated copy of the layout, so nothing restates it by hand.

The source is tools/layout.py (actions, default binds, wheel slices, button names per pad)
plus site/data/hotspots.json (where each button sits on the real controller photos).
From them this writes:

  site/data/layout.json   what the website's button map and wheel show
  README.md               the tables between <!-- generated:NAME --> and <!-- /generated --> markers

    python site/build.py          write the files
    python site/build.py --check  fail if a committed copy is out of date (CI and the tests run this)

Standard library only.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import layout as L  # noqa: E402
from common import VERSION  # noqa: E402

LAYOUT_JSON = os.path.join(HERE, "data", "layout.json")
HOTSPOTS = os.path.join(HERE, "data", "hotspots.json")
README = os.path.join(ROOT, "README.md")
# the order the map lists its controls, left side then right side (also the README tables)
ORDER_LEFT = ["lt", "lb", "ls", "ls_click", "view", "dup", "dright", "ddown", "dleft"]
ORDER_RIGHT = ["rt", "rb", "y", "x", "b", "a", "menu", "rs", "rs_click"]


def hotspots():
    with open(HOTSPOTS, encoding="utf-8") as f:
        return json.load(f)["pads"]


def build():
    lay = L.default_layout()
    spots = hotspots()
    pads = {}
    for kind in L.PAD_ORDER:
        h = spots[kind]
        pads[kind] = {"title": L.PADS[kind]["title"], "names": L.part_names(kind),
                      "controls": L.part_controls(lay, kind),
                      "img": h["img"], "w": h["w"], "h": h["h"], "alt": h["alt"], "spots": h["spots"]}
    wheel = [{"key": k, "label": lbl} for k, lbl in L.wheel_slices(lay)]
    return {"version": VERSION, "pads": pads, "wheel": wheel}


def table(kind):
    """The controls of one pad as a markdown table, in the order the map lists them."""
    names, controls = L.part_names(kind), L.part_controls(L.default_layout(), kind)
    rows = [(names[p], controls[p]) for p in ORDER_LEFT + ORDER_RIGHT if p in controls]
    return "\n".join(["| On the pad | Does |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows])


def wheel_text():
    keys = [(k, lbl) for k, lbl in L.wheel_slices(L.default_layout())]
    return ("Slices, clockwise from the empty top: "
            + ", ".join(f"{k} = {lbl}" for k, lbl in keys) + ".")


def blocks():
    out = {f"map-{k}": table(k) for k in L.PAD_ORDER}
    out["wheel"] = wheel_text()
    return out


BLOCK = re.compile(r"(<!-- generated:([a-z0-9-]+) -->\n)(.*?)(\n?<!-- /generated -->)", re.S)


def readme_text(text):
    gen = blocks()
    seen = set()

    def fill(m):
        name = m.group(2)
        if name not in gen:
            raise SystemExit(f"README.md has a generated block {name!r} that build.py does not know.")
        seen.add(name)
        return m.group(1) + gen[name] + "\n<!-- /generated -->"
    text = BLOCK.sub(fill, text)
    missing = set(gen) - seen
    if missing:
        raise SystemExit("README.md is missing generated blocks: " + ", ".join(sorted(missing)))
    return text


def outputs():
    with open(README, encoding="utf-8", newline="") as f:
        readme = f.read().replace("\r\n", "\n")
    return {LAYOUT_JSON: json.dumps(build(), indent=1, ensure_ascii=False) + "\n", README: readme_text(readme)}


def main():
    outs = outputs()
    if "--check" in sys.argv:
        stale = []
        for path, text in outs.items():
            cur = open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n") if os.path.exists(path) else ""
            if cur != text:
                stale.append(os.path.relpath(path, ROOT))
        if stale:
            sys.exit("out of date: " + ", ".join(stale) + " (run python site/build.py)")
        print("generated copies are up to date")
        return
    for path, text in outs.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
