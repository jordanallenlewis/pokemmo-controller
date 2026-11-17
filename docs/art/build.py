"""Draws every picture the README shows, as SVG, in a light and a dark variant.

    python docs/art/build.py          rewrite docs/img/*.svg

Same look as the website (pokemmocontroller.com): the colours come from
brand/tokens.json (site/styles.css is checked against it), and the logo, the PokeMMO
wordmark and the feature icons are read from site/ so they cannot drift. The controller
outlines are drawn here, not photographed or copied, and carry no brand marks. Standard library only.

The pictures describe the default layout (tools/layout.py). If a default changes,
change PADS / WHEEL below in the same commit; tests/test_art.py fails when the
pictures and the layout disagree.
"""
import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "img"
FONT = "'Bricolage Grotesque','Geist','Segoe UI Variable Display','Segoe UI',Inter,'SF Pro Display',-apple-system,'Helvetica Neue',Arial,sans-serif"

TOKENS = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))
_k = TOKENS["css"]
THEMES = {
    "light": TOKENS["light"],
    # dark = the website's own colours, read from the shared tokens
    "dark": dict(bg=_k["--bg"], card=_k["--surface"], ink=_k["--ink"], mute=_k["--muted"], line="#2f333b",
                 body=_k["--surface-2"], body2="#30353d", edge="#4a505c", accent=_k["--yellow"],
                 fill=_k["--yellow"], on=_k["--yellow-ink"], soft="#34301f", amber=_k["--yellow"],
                 dim="#5d636f", screen="#0b0d10", glow="#1a1d23"),
}


def site_svg(name):
    """Inner markup and viewBox of a site asset (logo, wordmark): the README draws the same files the site shows."""
    t = (ROOT / "site" / "assets" / name).read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', t).group(1)
    inner = t[t.index(">", t.index("<svg")) + 1:t.rindex("</svg>")]
    return vb, inner


def site_icons():
    """The six feature-card icons, straight from site/index.html (24x24 line icons)."""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    ic = re.findall(r'<svg class="card-ico"[^>]*>(.*?)</svg>', html, re.S)
    assert len(ic) == 6, "site/index.html no longer has six feature icons"
    return ic


# ------------------------------------------------------------------ what each pad prints
# role -> printed name, per pad. Roles are SDL3 positions (layout.py): the physical button.
PADS = {
    "xbox": dict(title="Xbox", sub="Xbox One, Series and 360 pads", shape="pad", swap=False,
                 face=("A", "B", "X", "Y"), view="View", menu="Menu", lb="LB", rb="RB", lt="LT", rt="RT",
                 l3="L3", r3="R3", facecolors=True),
    "playstation": dict(title="PlayStation", sub="DualSense and DualShock 4", shape="ps", swap=False,
                        face=("Cross", "Circle", "Square", "Triangle"), view="Create", menu="Options", lb="L1", rb="R1",
                        lt="L2", rt="R2", l3="L3", r3="R3", facecolors=False),
    "switch": dict(title="Switch Pro", sub="Nintendo Switch Pro Controller", shape="pad", swap=True,
                   face=("B", "A", "Y", "X"), view="−", menu="+", lb="L", rb="R", lt="ZL", rt="ZR",
                   l3="L3", r3="R3", facecolors=False),
    "deck": dict(title="Steam Deck", sub="Desktop Mode and Game Mode (Game Mode not yet tested on a Deck)",
                 shape="deck", swap=False, face=("A", "B", "X", "Y"), view="View", menu="Menu",
                 lb="L1", rb="R1", lt="L2", rt="R2", l3="L3", r3="R3", facecolors=False),
    "legion": dict(title="Lenovo Legion Go S", sub="Legion Go S, with the Steam layout built for it",
                   shape="hand", swap=False, face=("A", "B", "X", "Y"), view="View", menu="Menu",
                   lb="LB", rb="RB", lt="LT", rt="RT", l3="L3", r3="R3", facecolors=False),
}

# The default layout, as the pictures show it (tools/layout.py DEFAULT_BINDS).
DPAD = ("Hotbar 1", "Hotbar 2", "Hotbar 3", "Hotbar 4")          # up, right, down, left
WHEEL = [("N", "Pokédex"), ("I", "Egg Incubators"), ("C", "Trainer Card"), ("V", "Friends"),
         ("P", "Global Trade Link"), ("6", "Hotbar 6"), ("7", "Hotbar 7"), ("8", "Hotbar 8"),
         ("9", "Hotbar 9"), ("F12", "Hide GUI")]                  # clockwise after the empty top slice


def svg(w, h, t, body, title, desc=""):
    c = THEMES[t]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d" font-family="{FONT}">\n'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc or title)}</desc>\n'
            f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>\n{body}\n</svg>\n')


def text(x, y, s, size, fill, weight=400, anchor="start", extra=""):
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" {extra}>{esc(s)}</text>')


# ------------------------------------------------------------------ the controller outlines
def body_gamepad(c, ps=False):
    top = -150
    path = ("M -250,{t} C -150,{t2} 150,{t2} 250,{t} C 330,-140 382,-40 396,70 C 414,168 380,214 330,206 "
            "C 282,198 252,126 206,104 C 120,84 -120,84 -206,104 C -252,126 -282,198 -330,206 "
            "C -380,214 -414,168 -396,70 C -382,-40 -330,-140 -250,{t} Z").format(t=top, t2=top - 24)
    s = f'<path d="{path}" fill="{c["body"]}" stroke="{c["edge"]}" stroke-width="3"/>'
    if ps:
        s += f'<rect x="-92" y="-128" width="184" height="86" rx="26" fill="{c["body2"]}" stroke="{c["edge"]}" stroke-width="2"/>'
    return s


def body_hand(c, wide, legion=False):
    w, h = (430, 175) if wide else (410, 170)
    s = (f'<rect x="{-w}" y="{-h}" width="{2*w}" height="{2*h}" rx="92" fill="{c["body"]}" stroke="{c["edge"]}" stroke-width="3"/>'
         f'<rect x="-196" y="-118" width="392" height="236" rx="16" fill="{c["screen"]}" stroke="{c["edge"]}" stroke-width="2"/>')
    s += (f'<text x="0" y="6" font-size="26" font-weight="700" fill="#e4e7ff" text-anchor="middle">PokeMMO</text>')
    return s


def stick(c, x, y, r=38, hl=False):
    ring = c["amber"] if hl else c["edge"]
    return (f'<circle cx="{x}" cy="{y}" r="{r+9}" fill="{c["body2"]}" stroke="{c["edge"]}" stroke-width="2"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c["card"]}" stroke="{ring}" stroke-width="3"/>'
            f'<circle cx="{x}" cy="{y}" r="{r*0.55:g}" fill="none" stroke="{c["line"]}" stroke-width="2"/>')


def dpad(c, x, y, k=15):
    a, b = k, k * 3
    return (f'<path d="M {x-a},{y-b} h {2*a} v {b-a} h {b-a} v {2*a} h {-(b-a)} v {b-a} h {-2*a} v {-(b-a)} '
            f'h {-(b-a)} v {-2*a} h {b-a} z" fill="{c["card"]}" stroke="{c["edge"]}" stroke-width="3"/>')


PS_SHAPES = {"Cross": "#5b8def", "Circle": "#e5604f", "Square": "#d77bb0", "Triangle": "#2fb59a"}


def ps_glyph(name, x, y, c):
    col = PS_SHAPES[name]
    st = f'fill="none" stroke="{col}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"'
    if name == "Cross":
        return f'<path d="M {x-8},{y-8} L {x+8},{y+8} M {x+8},{y-8} L {x-8},{y+8}" {st}/>'
    if name == "Circle":
        return f'<circle cx="{x}" cy="{y}" r="9" {st}/>'
    if name == "Square":
        return f'<rect x="{x-8}" y="{y-8}" width="16" height="16" {st}/>'
    return f'<path d="M {x},{y-10} L {x+9.5},{y+7} L {x-9.5},{y+7} Z" {st}/>'


def face(c, x, y, glyphs, colored):
    pal = {"A": "#3fa05b", "B": "#d4483f", "X": "#3b7de0", "Y": "#e4b222"}
    pos = [(0, 38), (38, 0), (-38, 0), (0, -38)]        # bottom, right, left, top
    s = ""
    for (dx, dy), g in zip(pos, glyphs):
        fill = c["card"]
        ink = c["mute"]
        if colored:
            fill, ink = pal[g], "#ffffff"
        s += f'<circle cx="{x+dx}" cy="{y+dy}" r="21" fill="{fill}" stroke="{c["edge"]}" stroke-width="2.5"/>'
        px, py = x + dx, y + dy
        if g in PS_SHAPES:
            s += ps_glyph(g, px, py, c)
        else:
            s += text(px, py + 8, g, 22, ink, 700, "middle")
    return s


def capsule(c, x, y, w=34, h=15, hl=False):
    fill = c["amber"] if hl else c["card"]
    return f'<rect x="{x-w/2:g}" y="{y-h/2:g}" width="{w}" height="{h}" rx="{h/2:g}" fill="{fill}" stroke="{c["edge"]}" stroke-width="2.5"/>'


def shoulder(c, x, y, w, trig_h=0, mirror=False):
    """Bumper bar at (x,y) and a trigger behind it."""
    s = ""
    if trig_h:
        s += (f'<rect x="{x-w*0.42:g}" y="{y-trig_h-16:g}" width="{w*0.84:g}" height="{trig_h}" rx="16" '
              f'fill="{c["body2"]}" stroke="{c["edge"]}" stroke-width="2.5"/>')
    s += (f'<rect x="{x-w/2:g}" y="{y-16:g}" width="{w}" height="30" rx="15" fill="{c["body2"]}" '
          f'stroke="{c["edge"]}" stroke-width="2.5"/>')
    return s


def pad_art(c, cfg):
    """Return (svg group at origin, anchors). Anchors are where a leader line should land."""
    shape = cfg["shape"]
    A = {}
    if shape in ("pad", "ps"):
        ps = shape == "ps"
        g = body_gamepad(c, ps)
        ls, dp = ((-205, -42), (-122, 62)) if not ps else ((-122, 62), (-205, -42))
        fc, rs = (205, -42), (122, 62)
        g += shoulder(c, -255, -168, 190, 46) + shoulder(c, 255, -168, 190, 46)
        g += dpad(c, *dp) + stick(c, *ls, hl=True) + stick(c, *rs, hl=True) + face(c, *fc, cfg["face"], cfg["facecolors"])
        vx, mx, vy = (-52, 52, -66) if not ps else (-150, 150, -96)
        g += capsule(c, vx, vy, hl=True) + capsule(c, mx, vy)
        if not ps:
            g += f'<circle cx="0" cy="-112" r="19" fill="{c["card"]}" stroke="{c["edge"]}" stroke-width="2.5"/>'
        else:
            g += f'<circle cx="0" cy="48" r="14" fill="{c["card"]}" stroke="{c["edge"]}" stroke-width="2.5"/>'
        A = dict(lt=(-255, -208), lb=(-255, -168), rt=(255, -208), rb=(255, -168), ls=ls, rs=rs, dpad=dp,
                 view=(vx, vy), menu=(mx, vy), face=fc)
        # face buttons by position
        A.update(fb=(fc[0], fc[1] + 38), fr=(fc[0] + 60, fc[1]), fl=(fc[0] - 38, fc[1]), ft=(fc[0], fc[1] - 38))
    else:
        wide = shape == "deck"
        g = body_hand(c, wide)
        g += shoulder(c, -300, -192, 170, 40) + shoulder(c, 300, -192, 170, 40)
        ls, dp, rs, fc = (-300, -86), (-300, 78), (300, 78), (300, -86)
        g += stick(c, *ls, r=34, hl=True) + stick(c, *rs, r=34, hl=True) + dpad(c, *dp, k=13)
        g += face(c, *fc, cfg["face"], False)
        vx, mx, vy = (-246, 246, -6)
        g += capsule(c, vx, vy, 20, 12, hl=True) + capsule(c, mx, vy, 20, 12)
        if shape == "deck":      # the two touch pads under the sticks
            for x in (-228, 228):
                g += f'<rect x="{x-34}" y="94" width="68" height="62" rx="12" fill="{c["body2"]}" stroke="{c["edge"]}" stroke-width="2"/>'
        A = dict(lt=(-300, -232), lb=(-300, -192), rt=(300, -232), rb=(300, -192), ls=ls, rs=rs, dpad=dp,
                 view=(vx, vy), menu=(mx, vy), face=fc)
        A.update(fb=(fc[0], fc[1] + 38), fr=(fc[0] + 60, fc[1]), fl=(fc[0] - 38, fc[1]), ft=(fc[0], fc[1] - 38))
    return g, A


def face_roles(cfg):
    """(confirm, cancel, key x, key y) printed names, from SDL3 position names."""
    bottom, right, left, top = cfg["face"]
    if cfg["swap"]:              # layout buttons swap in pairs: A<->B, X<->Y (tools/layout.py)
        return right, bottom, top, left
    return bottom, right, left, top


# ------------------------------------------------------------------ callout cards
def card(c, x, y, w, h, chip, title, sub=None, lines=None):
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2"/>')
    s += text(x + 24, y + 33, chip, 17, c["accent"], 700, extra='letter-spacing=".6"')
    if lines:
        for i, (k, v) in enumerate(lines):
            yy = y + 66 + i * 30
            s += text(x + 24, yy, k, 20, c["mute"], 600) + text(x + 24 + 100, yy, v, 22, c["ink"], 650)
    else:
        s += text(x + 24, y + 68, title, 26, c["ink"], 700)
        if sub:
            s += text(x + 24, y + 96, sub, 17, c["mute"])
    return s


def leader(c, pts):
    (x2, y2) = pts[-1]
    return (f'<polyline points="{" ".join(f"{x:g},{y:g}" for x, y in pts)}" fill="none" stroke="{c["accent"]}" '
            f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/>'
            f'<circle cx="{x2:g}" cy="{y2:g}" r="6.5" fill="{c["accent"]}" stroke="{c["bg"]}" stroke-width="2.5"/>')


def specs(cfg):
    """The cards both layouts show: (left side dict, right side dict) of key -> (chip, title, sub, lines)."""
    confirm, cancel, kx, ky = face_roles(cfg)
    left = {
        "lt": (cfg["lt"], "Previous hotbar page", None, None),
        "lb": (cfg["lb"], "Focus Ring", "Highlights anything on screen", None),
        "ls": ("Left stick", None, None, [("Stick", "Move"), (cfg["l3"], "Team")]),
        "dpad": ("D-pad", None, None, [("↑ / →", "Hotbar 1 / 2"), ("↓ / ←", "Hotbar 3 / 4")]),
        "view": (cfg["view"], "Map", "Hotbar 5: keep the Town Map in slot 5", None),
    }
    right = {
        "rt": (cfg["rt"], "Next hotbar page", None, None),
        "rb": (cfg["rb"], "Bag", None, None),
        "face": ("Face buttons", None, None, [(confirm, "Confirm"), (cancel, "Cancel"), (kx, "Key X"), (ky, "Key Y")]),
        "rs": ("Right stick", None, None, [("Stick", "Wheel"), (cfg["r3"], "Screenshot")]),
        "menu": (cfg["menu"], "Game Menu", "Party, settings and more", None),
    }
    return left, right


def button_map_phone(t, key):
    """The same map for a narrow screen: the pad on top with numbered spots, big numbered cards below."""
    c = THEMES[t]
    cfg = PADS[key]
    W = 900
    g, A = pad_art(c, cfg)
    L_, R_ = specs(cfg)
    order = [("lt", L_), ("lb", L_), ("view", L_), ("ls", L_), ("dpad", L_),
             ("rt", R_), ("rb", R_), ("menu", R_), ("face", R_), ("rs", R_)]
    anchor = {}
    sc, cx, cy = 0.9, W / 2, 400
    body = text(40, 84, "Default layout", 52, c["ink"], 800)
    body += f'<g transform="translate({cx:g},{cy}) scale({sc})">{g}</g>'
    cards = marks = ""
    y0, ch, gap = 640, 0, 20
    ys = [y0, y0]
    for n, (name, spec) in enumerate(order, 1):
        chip, title, sub, lines = spec[name]
        ax, ay = A[anchor.get(name, name)]
        px, py = cx + ax * sc, cy + ay * sc
        marks += (f'<circle cx="{px:g}" cy="{py:g}" r="17" fill="{c["fill"]}" stroke="{c["bg"]}" stroke-width="3"/>'
                  + text(px, py + 7, str(n), 20, c["on"], 800, "middle"))
        col = 0 if n <= 5 else 1
        h = (46 + 44 * len(lines) + 24) if lines else 150
        x, y = 30 + col * 435, ys[col]
        cards += (f'<rect x="{x}" y="{y}" width="420" height="{h}" rx="20" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
                  f'<circle cx="{x+40}" cy="{y+44}" r="22" fill="{c["fill"]}"/>' + text(x + 40, y + 53, str(n), 26, c["on"], 800, "middle")
                  + text(x + 78, y + 52, chip, 26, c["accent"], 700))
        if lines:
            for i, (k, v) in enumerate(lines):
                cards += text(x + 28, y + 100 + i * 44, k, 28, c["mute"], 600) + text(x + 28 + 150, y + 100 + i * 44, v, 32, c["ink"], 700)
        else:
            cards += text(x + 28, y + 104, title, 33, c["ink"], 700)
            if sub:
                cards += text(x + 28, y + 134, sub.replace("Hotbar 5: keep the Town Map in slot 5", "Put the Town Map in slot 5"), 22, c["mute"])
        ys[col] += h + gap
    H = max(ys) + 30
    body += marks + cards
    return svg(W, H, t, body, f"{cfg['title']} button map (narrow screens)",
               f"The default layout on {cfg['title']}, as a numbered list of spots and actions.")


def button_map(t, key):
    c = THEMES[t]
    cfg = PADS[key]
    hand = cfg["shape"] in ("deck", "hand")
    W, H = 1900, 900
    cx, cy = 950, 590
    g, A = pad_art(c, cfg)
    confirm, cancel, kx, ky = face_roles(cfg)
    CW = 390
    lx, rx = 50, W - 50 - CW
    L_, R_ = specs(cfg)
    if hand:
        lorder, rorder = ["lt", "lb", "ls", "view", "dpad"], ["rt", "rb", "face", "menu", "rs"]
        top = []
    else:
        lorder, rorder = ["lt", "lb", "ls", "dpad"], ["rt", "rb", "face", "rs"]
        top = [("view", "L"), ("menu", "R")]
    anchor = {"face": "fr"}
    lorder.sort(key=lambda n: A[anchor.get(n, n)][1])
    rorder.sort(key=lambda n: A[anchor.get(n, n)][1])
    height = lambda spec: 40 + 30 * len(spec[3]) + 28 if spec[3] else 124
    body = text(60, 92, "Default layout", 52, c["ink"], 800)
    body += text(60, 136, cfg["sub"], 22, c["mute"])
    body += text(W - 60, 92, "PokeMMO Controller Layout", 26, c["accent"], 700, "end")
    body += text(W - 60, 128, "One input does one action", 21, c["mute"], 400, "end")
    leaders = cards = ""
    endy = 0
    for side, order, spec, x in (("L", lorder, L_, lx), ("R", rorder, R_, rx)):
        y = 215
        for n, name in enumerate(order):
            chip, title, sub, lines = spec[name]
            h = height(spec[name])
            ax, ay = A[anchor.get(name, name)]
            ex = x + CW if side == "L" else x
            bus = (ex + 26 + 14 * n) if side == "L" else (ex - 26 - 14 * n)
            leaders += leader(c, [(ex, y + h / 2), (bus, y + h / 2), (bus, cy + ay), (cx + ax, cy + ay)])
            cards += card(c, x, y, CW, h, chip, title or "", sub, lines)
            y += h + 18
            endy = max(endy, y)
    for name, side in top:
        spec = (L_ if side == "L" else R_)[name]
        chip, title, sub, lines = spec
        ax, ay = A[name]
        w, h = 400, 124
        x = cx - 30 - w if side == "L" else cx + 30
        y = 178
        cards += card(c, x, y, w, h, chip, title, sub, None)
        leaders += leader(c, [(cx + ax, y + h), (cx + ax, cy + ay)])
    H = max(H, int(endy) + 70)
    body += f'<g transform="translate({cx},{cy})">{g}</g>' + leaders + cards
    body += text(W // 2, H - 44, "Tilt the right stick toward a slice and let go to use it. The wheel is below.",
                 22, c["mute"], 400, "middle")
    return svg(W, H, t, body, f"{cfg['title']} button map",
               f"Default layout on {cfg['title']}: " + "; ".join(
                   [f"{cfg['lb']} Focus Ring", f"{cfg['view']} Map (Hotbar 5)", f"{cfg['menu']} Game Menu",
                    f"{cfg['rb']} Bag", f"{confirm} confirm", f"{cancel} cancel",
                    f"{cfg['lt']}/{cfg['rt']} hotbar pages", "d-pad Hotbar 1 to 4", "right stick wheel"]))


# ------------------------------------------------------------------ the wheel
def polar(r, deg):
    a = math.radians(deg)
    return r * math.sin(a), -r * math.cos(a)


def wedge(r0, r1, a0, a1):
    x0, y0 = polar(r1, a0); x1, y1 = polar(r1, a1)
    x2, y2 = polar(r0, a1); x3, y3 = polar(r0, a0)
    return (f"M {x0:.2f},{y0:.2f} A {r1},{r1} 0 0 1 {x1:.2f},{y1:.2f} "
            f"L {x2:.2f},{y2:.2f} A {r0},{r0} 0 0 0 {x3:.2f},{y3:.2f} Z")


def wheel_group(c, hl=None, animate=False):
    n = 11
    step = 360 / n
    g = ""
    for k in range(n):
        a0, a1 = -step / 2 + k * step + 0.9, step / 2 + k * step - 0.9
        fill = c["card"]
        if k == 0:
            fill = "none"
        dash = 'stroke-dasharray="10 9"' if k == 0 else ""
        g += (f'<path id="s{k}" d="{wedge(170, 330, a0, a1)}" fill="{fill}" stroke="{c["line"] if k else c["dim"]}" '
              f'stroke-width="3" {dash}/>')
        if k:
            key, name = WHEEL[k - 1]
            x, y = polar(250, k * step)
            g += (f'<rect x="{x-31:.1f}" y="{y-20:.1f}" width="62" height="40" rx="10" fill="{c["soft"]}"/>'
                  + text(round(x, 1), round(y + 9, 1), key, 26, c["accent"], 800, "middle"))
            lx, ly = polar(378, k * step)
            anchor = "middle" if abs(lx) < 40 else ("start" if lx > 0 else "end")
            g += text(round(lx + (14 if anchor == "start" else -14 if anchor == "end" else 0), 1),
                      round(ly + 9, 1), name, 28, c["ink"], 650, anchor)
    x, y = polar(250, 0)
    g += text(round(x, 1), round(y + 8, 1), "does nothing", 20, c["mute"], 500, "middle")
    g += (f'<circle r="140" fill="{c["bg"]}" stroke="{c["dim"]}" stroke-width="3" stroke-dasharray="10 9"/>'
          + text(0, -4, "Let go", 28, c["ink"], 700, "middle") + text(0, 30, "here to cancel", 20, c["mute"], 400, "middle"))
    return g


def wheel(t):
    c = THEMES[t]
    W, H = 1400, 1000
    body = f'<g transform="translate(700,500) scale(1.04)">{wheel_group(c)}</g>'
    body += text(60, 84, "The right-stick wheel", 44, c["ink"], 800)
    body += text(60, 124, "Tilt the stick toward a slice, let go. One key press, once.", 22, c["mute"])
    return svg(W, H, t, body, "The right-stick wheel",
               "Eleven slices clockwise from the top. The top slice does nothing. Then " +
               ", ".join(n for _, n in WHEEL) + ". Letting go in the centre cancels.")


def wheel_demo(t):
    """An animated drawing of the wheel (an illustration, not game footage)."""
    c = THEMES[t]
    W, H = 1400, 900
    body = f'<g transform="translate(700,470) scale(.98)">{wheel_group(c)}'
    seq = [3, 5, 8, 11, 6, 1]          # slices visited (1 = Pokédex ... 10 = Hide GUI; 0 is empty)
    dur = len(seq) * 1.6
    vals = ";".join(f"{(i)/len(seq):.4f}" for i in range(len(seq))) + ";1"
    for k in range(1, 11):
        a0, a1 = -step_half() + k * step_deg() + 0.9, step_half() + k * step_deg() - 0.9
        on = [1 if s == k else 0 for s in seq] + [0]
        # fade a highlight in while the stick points here
        body += (f'<path d="{wedge(170, 330, a0, a1)}" fill="{c["fill"]}" opacity="0">'
                 f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
                 f'keyTimes="{vals}" values="{";".join(str(0.9 * v) for v in on)}"/></path>')
    body += "</g>"
    body += text(60, 84, "Point. Let go. One key press.", 44, c["ink"], 800)
    body += text(60, 124, "A drawing of the wheel, not game footage. The top slice and the middle do nothing.", 22, c["mute"])
    return svg(W, H, t, body, "The wheel, animated", "The wheel highlights one slice at a time, as the right stick moves.")


def step_deg():
    return 360 / 11


def step_half():
    return 360 / 22


# ------------------------------------------------------------------ small helpers
def wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if line and len(line) + 1 + len(w) > n:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return out + [line]


# ------------------------------------------------------------------ install steps
STEPS = [("1", "Close PokeMMO", "Leave Steam open. The installer restarts it if it must, never under a running game."),
         ("2", "Paste one line", "Your system's line from below. Nothing to install first, no admin rights."),
         ("3", "Play from Steam", "Launch PokeMMO from your Steam library. Done in about a minute.")]


def steps(t):
    c = THEMES[t]
    cw, gap, pad = 470, 42, 60
    W, H = pad * 2 + 3 * cw + 2 * gap, 360
    body = ""
    for i, (n, h, d) in enumerate(STEPS):
        x = pad + i * (cw + gap)
        body += f'<rect x="{x}" y="40" width="{cw}" height="280" rx="20" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2"/>'
        body += f'<circle cx="{x+62}" cy="108" r="30" fill="{c["fill"]}"/>' + text(x + 62, 119, n, 32, c["on"], 800, "middle")
        body += text(x + 112, 119, h, 34, c["ink"], 750)
        for j, ln in enumerate(wrap(d, 34)):
            body += text(x + 36, 178 + j * 34, ln, 24, c["mute"])
        if i < 2:
            body += f'<path d="M {x+cw+8},180 l 28,0 m -10,-10 l 10,10 l -10,10" fill="none" stroke="{c["accent"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    return svg(W, H, t, body, "Install in three steps", "Close PokeMMO, paste one line for your system, play from Steam.")


def steps_phone(t):
    c = THEMES[t]
    W, ch, gap = 900, 250, 26
    body = ""
    for i, (n, h, d) in enumerate(STEPS):
        y = 30 + i * (ch + gap)
        body += f'<rect x="30" y="{y}" width="{W-60}" height="{ch}" rx="24" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
        body += f'<circle cx="104" cy="{y+68}" r="38" fill="{c["fill"]}"/>' + text(104, y + 82, n, 42, c["on"], 800, "middle")
        body += text(166, y + 82, h, 48, c["ink"], 750)
        for j, ln in enumerate(wrap(d, 42)):
            body += text(66, y + 156 + j * 42, ln, 32, c["mute"])
    H = 30 + 3 * (ch + gap)
    return svg(W, H, t, body, "Install in three steps", "Close PokeMMO, paste one line for your system, play from Steam.")


# ------------------------------------------------------------------ feature cards
def icon(c, i, x, y):
    """The site's own 24x24 line icon number i, scaled to 64x64."""
    return (f'<g transform="translate({x},{y}) scale(2.667)" fill="none" stroke="{c["accent"]}" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round">{site_icons()[i]}</g>')


# Same six cards, in the same order and words, as the website's features section.
FEATURES = [("The game's own controller support", "Your binds go straight into PokeMMO's settings. Nothing sits between your controller and the game."),
            ("Within PokeMMO's rules", "One input does one thing. No turbo, no macros, no sequences, and the tool refuses any layout that tries."),
            ("Remap in your browser", "Pick your controller, change any button, watch the map update, press Apply. Runs on your computer only."),
            ("Updates keep your layout", "Run the same command to update. Uninstall puts every file back exactly as it was."),
            ("Finds the game by itself", "Windows, the macOS app, the Linux zip, Flatpak and Snap. No settings to hunt for, no admin rights."),
            ("Your whole hotbar", "Slots 1-4 on the D-pad, slot 5 on View (which also opens the town map), 6-9 on the wheel, and the Focus Ring on LB to reach any item.")]


def features(t):
    c = THEMES[t]
    W, cw, ch, gap = 1600, 755, 220, 30
    body = ""
    for i, (h, d) in enumerate(FEATURES):
        x, y = 30 + (i % 2) * (cw + gap), 30 + (i // 2) * (ch + gap)
        body += f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="22" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
        body += f'<rect x="{x+30}" y="{y+34}" width="92" height="92" rx="22" fill="{c["soft"]}"/>' + icon(c, i, x + 44, y + 48)
        body += text(x + 152, y + 62, h, 33, c["ink"], 800)
        for j, ln in enumerate(wrap(d, 46)):
            body += text(x + 152, y + 104 + j * 34, ln, 26, c["mute"])
    H = 30 + 3 * (ch + gap)
    return svg(W, H, t, body, "What you get", "; ".join(f"{h}: {d}" for h, d in FEATURES))


def features_phone(t):
    c = THEMES[t]
    W, ch, gap = 900, 270, 22
    body = ""
    for i, (h, d) in enumerate(FEATURES):
        y = 24 + i * (ch + gap)
        body += f'<rect x="24" y="{y}" width="{W-48}" height="{ch}" rx="24" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
        body += f'<rect x="54" y="{y+34}" width="104" height="104" rx="24" fill="{c["soft"]}"/>' + icon(c, i, 54 + 20, y + 34 + 20)
        for j, ln in enumerate(wrap(h, 24)):
            body += text(190, y + 66 + j * 46, ln, 40, c["ink"], 800)
        off = 66 + 46 * len(wrap(h, 24)) + 14
        for j, ln in enumerate(wrap(d, 40)):
            body += text(190, y + off + j * 36, ln, 28, c["mute"])
    H = 24 + 6 * (ch + gap)
    return svg(W, H, t, body, "What you get", "; ".join(f"{h}: {d}" for h, d in FEATURES))


# ------------------------------------------------------------------ hero, strip and buttons
def logo_mark(x, y, h):
    vb, inner = site_svg("logo.svg")
    w = h * 420 / 222
    return f'<svg x="{x}" y="{y}" width="{w:g}" height="{h}" viewBox="{vb}" shape-rendering="crispEdges">{inner}</svg>'


def wordmark(x, y, h):
    vb, inner = site_svg("pokemmo-wordmark.svg")
    w = h * 294 / 39
    return f'<svg x="{x}" y="{y}" width="{w:g}" height="{h}" viewBox="{vb}" shape-rendering="crispEdges">{inner}</svg>'


def chips(c, x, y, names, size, pad, h):
    s = ""
    for n in names:
        w = len(n) * size * 0.62 + pad * 2
        s += (f'<rect x="{x:g}" y="{y}" width="{w:g}" height="{h}" rx="{h/2:g}" fill="none" stroke="{c["edge"]}" stroke-width="2"/>'
              + text(round(x + w / 2, 1), y + h / 2 + size * 0.35, n, size, c["mute"], 500, "middle"))
        x += w + 14
    return s


HERO_ALT = "PokeMMO Controller: play PokeMMO from the couch with an Xbox, PlayStation or Switch Pro controller"


def hero(t):
    """The website's hero. The banner is the site's dark ink in both variants, like the logo."""
    c = THEMES["dark"]
    W, H = 1600, 690
    g, _ = pad_art(c, PADS["xbox"])
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="36" fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="4"/>'
    body += f'<circle cx="1290" cy="340" r="240" fill="{c["glow"]}"/>'
    body += f'<g transform="translate(1290,370) scale(.6)">{g}</g>'
    body += logo_mark(80, 62, 64)
    body += (f'<text x="{80 + 64 * 420 / 222 + 22:g}" y="108" font-size="40" font-weight="700" fill="{c["ink"]}">PokeMMO '
             f'<tspan fill="{c["accent"]}">Controller</tspan></text>')
    body += text(80, 214, "FREE · OPEN SOURCE", 26, c["mute"], 500, extra='letter-spacing="3"')
    body += text(80, 330, "Play", 112, c["ink"], 800) + wordmark(318, 258, 72)
    body += text(80, 440, "from the couch", 112, c["ink"], 800)
    body += text(80, 516, "Every action on your controller: battles, hotbar, Bag, GTL, Pokédex.", 28, c["mute"], 400)
    body += text(80, 556, "One command to install, and it stays out of your way.", 28, c["mute"], 400)
    body += chips(c, 80, 596, ["Windows", "macOS", "Linux", "Steam Deck", "Legion Go"], 22, 22, 42)
    return svg(W, H, "dark", body, "PokeMMO Controller", HERO_ALT).replace(
        f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>\n', "")


def hero_phone(t):
    c = THEMES["dark"]
    W, H = 900, 1180
    g, _ = pad_art(c, PADS["xbox"])
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="40" fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="4"/>'
    body += f'<circle cx="450" cy="930" r="230" fill="{c["glow"]}"/>'
    body += f'<g transform="translate(450,940) scale(.8)">{g}</g>'
    body += logo_mark(56, 56, 60)
    body += (f'<text x="{56 + 60 * 420 / 222 + 20:g}" y="100" font-size="38" font-weight="700" fill="{c["ink"]}">PokeMMO '
             f'<tspan fill="{c["accent"]}">Controller</tspan></text>')
    body += text(56, 222, "FREE · OPEN SOURCE", 26, c["mute"], 500, extra='letter-spacing="3"')
    body += text(56, 318, "Play", 104, c["ink"], 800) + wordmark(282, 254, 64)
    body += text(56, 424, "from the couch", 104, c["ink"], 800)
    body += text(56, 500, "Every action on your controller:", 33, c["mute"], 400)
    body += text(56, 544, "battles, hotbar, Bag, GTL, Pokédex.", 33, c["mute"], 400)
    body += text(56, 588, "One command to install.", 33, c["mute"], 400)
    body += chips(c, 56, 622, ["Windows", "macOS", "Linux"], 24, 24, 46)
    body += chips(c, 56, 682, ["Steam Deck", "Legion Go"], 24, 24, 46)
    return svg(W, H, "dark", body, "PokeMMO Controller", HERO_ALT).replace(
        f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>\n', "")


STRIP = [("20+", "actions on the pad"), ("1", "command to install"), ("0", "apps to keep open"), ("1 = 1", "one press, one action")]


def strip(t):
    c = THEMES[t]
    W, H = 1600, 190
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="28" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="3"/>'
    cw = (W - 6) / 4
    for i, (n, d) in enumerate(STRIP):
        x = 3 + cw * i + cw / 2
        if i:
            body += f'<path d="M {3+cw*i:g},44 V {H-44}" stroke="{c["line"]}" stroke-width="2"/>'
        body += text(round(x, 1), 94, n, 62, c["accent"], 800, "middle") + text(round(x, 1), 138, d, 26, c["mute"], 500, "middle")
    return svg(W, H, t, body, "At a glance", "; ".join(f"{n} {d}" for n, d in STRIP))


def strip_phone(t):
    c = THEMES[t]
    W, H = 900, 380
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="32" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="3"/>'
    body += f'<path d="M 450,40 V {H-40} M 40,190 H {W-40}" stroke="{c["line"]}" stroke-width="2"/>'
    for i, (n, d) in enumerate(STRIP):
        x, y = 225 + (i % 2) * 450, 118 + (i // 2) * 190
        body += text(x, y, n, 74, c["accent"], 800, "middle") + text(x, y + 50, d, 29, c["mute"], 500, "middle")
    return svg(W, H, t, body, "At a glance", "; ".join(f"{n} {d}" for n, d in STRIP))


def os_icon(c, kind, x, y):
    """Drawn with paths only: no font glyphs (the Apple character and '>_' depend on the viewer's fonts)."""
    f = c["on"]
    st = f'fill="none" stroke="{f}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "win":
        return "".join(f'<rect x="{x+dx}" y="{y+dy}" width="14" height="14" rx="2" fill="{f}"/>' for dx in (0, 17) for dy in (0, 17))
    if kind == "mac":      # a monitor on a stand (a drawn computer, no brand mark)
        return (f'<rect x="{x}" y="{y+1}" width="31" height="21" rx="4" {st}/>'
                f'<path d="M {x+15.5},{y+22} V {y+28} M {x+8},{y+29} H {x+23}" {st}/>')
    return (f'<rect x="{x}" y="{y}" width="31" height="31" rx="8" {st}/>'
            f'<path d="M {x+8},{y+10} L {x+15},{y+16} L {x+8},{y+22} M {x+17},{y+23} H {x+24}" {st}/>')


def button(t, kind, title, sub):
    c = THEMES[t]
    W, H = 420, 110
    bg = c["fill"]
    body = (f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="22" fill="{bg}"/>'
            + os_icon(c, kind, 34, 39)
            + text(86, 52, title, 30, c["on"], 800) + text(86, 82, sub, 19, c["on"], 400, extra='opacity=".85"'))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="{esc(title)}" font-family="{FONT}">{body}</svg>\n')


def main(out=None):
    OUT = Path(out) if out else globals()["OUT"]
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for t in THEMES:
        def put(name, data):
            p = OUT / f"{name}-{t}.svg"
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(data)
            made.append(p.name)
        put("hero", hero(t))
        put("hero-phone", hero_phone(t))
        put("steps", steps(t))
        put("steps-phone", steps_phone(t))
        put("features", features(t))
        put("features-phone", features_phone(t))
        put("strip", strip(t))
        put("strip-phone", strip_phone(t))
        put("wheel", wheel(t))
        put("wheel-demo", wheel_demo(t))
        for k in PADS:
            put(f"map-{k}", button_map(t, k))
            put(f"map-{k}-phone", button_map_phone(t, k))
        put("get-windows", button(t, "win", "Windows", "One PowerShell line"))
        put("get-mac", button(t, "mac", "macOS", "One Terminal line"))
        put("get-linux", button(t, "lin", "Linux · Steam Deck", "One Terminal line"))
    print(f"wrote {len(made)} files to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
