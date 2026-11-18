"""Reads brand/tokens.json (W3C Design Tokens format 2025.10) and gives the flat shape the build,
the brand check, the art scripts and the tests use:
    {name, short, dark{}, light{}, type{}, radius, scale{px, rem, fluid, note}, fonts{allowed, note}}
Colours come out as "#rrggbb" or "rgba(r, g, b, .a)"; font stacks as CSS text.
Standard library only.
"""
import json, re
from pathlib import Path

PATH = Path(__file__).resolve().parent / "tokens.json"
EXT = "com.pokemmo-controller"


def _node(root, ref):
    cur = root
    for part in ref.strip("{}").split("."):
        cur = cur[part]
    return cur


def _value(root, tok):
    v = tok["$value"]
    if isinstance(v, str) and v.startswith("{"):
        return _value(root, _node(root, v))
    return v


def _color(v):
    r, g, b = (round(c * 255) for c in v["components"])
    a = v.get("alpha", 1)
    if a == 1:
        return v.get("hex") or "#%02x%02x%02x" % (r, g, b)
    return f"rgba({r}, {g}, {b}, {format(a, 'g').lstrip('0')})"


def _stack(names):
    return ", ".join(n if re.fullmatch(r"[A-Za-z0-9-]+", n) else f'"{n}"' for n in names)


def _dim(v):
    return v["value"]


def flat(path=PATH):
    t = json.loads(Path(path).read_text(encoding="utf-8"))
    ext = t["$extensions"][EXT]
    mode = lambda m: {k: _color(_value(t, tok)) for k, tok in t["color"][m].items()}
    return {
        "name": t["name"]["$value"], "short": t["short"]["$value"],
        "dark": mode("dark"), "light": mode("light"),
        "type": {k: _stack(v["$value"]) for k, v in t["font"].items() if not k.startswith("$")},
        "radius": f"{_dim(t['radius']['$value'])}{t['radius']['$value']['unit']}",
        "scale": {"px": {k: _dim(v["$value"]) for k, v in t["size"]["px"].items() if not k.startswith("$")},
                  "rem": {k: _dim(v["$value"]) for k, v in t["size"]["rem"].items() if not k.startswith("$")},
                  "fluid": ext["fluid"], "note": ext["scaleNote"]},
        "fonts": {"allowed": ext["fontsAllowed"], "note": ext["fontsNote"]},
    }
