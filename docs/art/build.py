"""Draws every picture the README shows, as SVG, in a light and a dark variant.

    python docs/art/build.py          rewrite docs/img/*.svg

One visual identity, all original: a deep indigo ink on soft paper (dark: a night
indigo), one indigo accent, one amber highlight. The controller outlines are drawn
here, not photographed or copied, and carry no brand marks. Standard library only.

The pictures describe the default layout (tools/layout.py). If a default changes,
change PADS / WHEEL below in the same commit; tests/test_art.py fails when the
pictures and the layout disagree.
"""
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

OUT = Path(__file__).resolve().parent.parent / "img"
FONT = "'Segoe UI Variable Display','Segoe UI',Inter,'SF Pro Display',-apple-system,'Helvetica Neue',Arial,sans-serif"

THEMES = {
    "light": dict(bg="#f4f5fb", card="#ffffff", ink="#141a2e", mute="#586180", line="#cdd2e4",
                  body="#e3e6f3", body2="#cfd4e8", edge="#b3bad4", accent="#4338ca",
                  soft="#e6e5fb", amber="#b45309", amber_soft="#fdebc8", dim="#aab1cb", on="#ffffff",
                  screen="#1b2140", glow="#d9dbf7"),
    "dark": dict(bg="#0e1122", card="#171b33", ink="#eef0fb", mute="#9aa3c4", line="#2c3358",
                 body="#232949", body2="#2f3760", edge="#434c7c", accent="#9a9cff",
                 soft="#262c57", amber="#fbbf24", amber_soft="#3b3010", dim="#4a537f", on="#0e1122",
                 screen="#0a0d1c", glow="#262c57"),
}

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
    s += (f'<text x="0" y="6" font-size="26" font-weight="700" fill="{c["accent"]}" text-anchor="middle" '
          f'opacity=".85">PokeMMO</text>')
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
    two = lambda a, b: [a, b]
    L_ = {
        "lt": (cfg["lt"], "Previous hotbar page", None, None),
        "lb": (cfg["lb"], "Focus Ring", "Highlights anything on screen", None),
        "ls": ("Left stick", None, None, [("Stick", "Move"), (cfg["l3"], "Team")]),
        "dpad": ("D-pad", None, None, [("↑ / →", "Hotbar 1 / 2"), ("↓ / ←", "Hotbar 3 / 4")]),
        "view": (cfg["view"], "Map", "Hotbar 5: keep the Town Map in slot 5", None),
    }
    R_ = {
        "rt": (cfg["rt"], "Next hotbar page", None, None),
        "rb": (cfg["rb"], "Bag", None, None),
        "face": ("Face buttons", None, None, [(confirm, "Confirm"), (cancel, "Cancel"), (kx, "Key X"), (ky, "Key Y")]),
        "rs": ("Right stick", None, None, [("Stick", "Wheel"), (cfg["r3"], "Screenshot")]),
        "menu": (cfg["menu"], "Game Menu", "Party, settings and more", None),
    }
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
    body = text(60, 92, cfg["title"], 52, c["ink"], 800)
    body += text(60, 136, "Default layout · " + cfg["sub"], 22, c["mute"])
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
        g += (f'<path id="s{k}" d="{wedge(170, 330, a0, a1)}" fill="{fill}" stroke="{c["line"] if k else c["dim"]}" '
              f'stroke-width="3" {"stroke-dasharray=\"10 9\"" if k == 0 else ""}/>')
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
        body += (f'<path d="{wedge(170, 330, a0, a1)}" fill="{c["accent"]}" opacity="0">'
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


# ------------------------------------------------------------------ install steps
def steps(t):
    c = THEMES[t]
    W, H = 1600, 360
    items = [("1", "Close PokeMMO", "Leave Steam open. The installer restarts it if it must, never under a running game."),
             ("2", "Paste one line", "Your system's line from below. Nothing to install first, no admin rights."),
             ("3", "Play from Steam", "Launch PokeMMO from your Steam library. Done in about a minute.")]
    body = ""
    cw, gap = 490, 45
    for i, (n, h, d) in enumerate(items):
        x = 60 + i * (cw + gap)
        body += f'<rect x="{x}" y="40" width="{cw}" height="280" rx="20" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2"/>'
        body += f'<circle cx="{x+62}" cy="108" r="30" fill="{c["accent"]}"/>' + text(x + 62, 119, n, 32, c["on"], 800, "middle")
        body += text(x + 112, 119, h, 34, c["ink"], 750)
        words, line, ly = d.split(), "", 178
        for w in words:
            if len(line + w) > 36:
                body += text(x + 36, ly, line.strip(), 22, c["mute"]); ly += 32; line = ""
            line += w + " "
        body += text(x + 36, ly, line.strip(), 22, c["mute"])
        if i < 2:
            body += f'<path d="M {x+cw+8},180 l 28,0 m -10,-10 l 10,10 l -10,10" fill="none" stroke="{c["accent"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    return svg(W, H, t, body, "Install in three steps", "Close PokeMMO, paste one line for your system, play from Steam.")


# ------------------------------------------------------------------ hero and buttons
def hero(t):
    c = THEMES[t]
    W, H = 1600, 520
    g, _ = pad_art(c, PADS["xbox"])
    body = f'<circle cx="1240" cy="270" r="215" fill="{c["glow"]}"/>'
    body += f'<g transform="translate(1240,300) scale(.64)">{g}</g>'
    body += text(80, 128, "POKEMMO", 26, c["accent"], 800, extra='letter-spacing="5"')
    body += text(80, 214, "Controller Layout", 84, c["ink"], 850)
    body += text(80, 272, "Every hotbar slot, the Bag, Party and GTL on your pad.", 28, c["mute"])
    body += text(80, 312, "A labeled wheel on the right stick. Change any button on screen.", 28, c["mute"])
    x = 80
    for label, wd in (("Xbox", 112), ("PlayStation", 160), ("Switch Pro", 150), ("Steam Deck", 156), ("Legion Go S", 156)):
        body += (f'<rect x="{x}" y="352" width="{wd}" height="42" rx="21" fill="{c["soft"]}"/>'
                 + text(x + wd / 2, 380, label, 20, c["accent"], 700, "middle"))
        x += wd + 14
    body += text(80, 452, "Windows · macOS · Linux · Steam Deck", 22, c["ink"], 650)
    body += text(80, 484, "One command. No admin rights. Nothing to install first.", 22, c["mute"], 400)
    return svg(W, H, t, body, "PokeMMO Controller Layout",
               "Play PokeMMO with an Xbox, PlayStation or Switch Pro controller on Windows, macOS, Linux and Steam Deck.")


def os_icon(c, kind, x, y):
    f = c["on"]
    if kind == "win":
        return "".join(f'<rect x="{x+dx}" y="{y+dy}" width="14" height="14" rx="2" fill="{f}"/>' for dx in (0, 17) for dy in (0, 17))
    if kind == "mac":
        return (f'<rect x="{x}" y="{y}" width="31" height="31" rx="8" fill="none" stroke="{f}" stroke-width="3"/>'
                + text(x + 15.5, y + 24, "⌘", 22, f, 700, "middle"))
    return (f'<rect x="{x}" y="{y}" width="31" height="31" rx="8" fill="none" stroke="{f}" stroke-width="3"/>'
            + text(x + 15.5, y + 22, ">_", 17, f, 800, "middle"))


def button(t, kind, title, sub):
    c = THEMES[t]
    W, H = 420, 110
    bg = c["accent"]
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
            p.write_text(data, encoding="utf-8", newline="\n")
            made.append(p.name)
        put("hero", hero(t))
        put("steps", steps(t))
        put("wheel", wheel(t))
        put("wheel-demo", wheel_demo(t))
        for k in PADS:
            put(f"map-{k}", button_map(t, k))
        put("get-windows", button(t, "win", "Windows", "One PowerShell line"))
        put("get-mac", button(t, "mac", "macOS", "One Terminal line"))
        put("get-linux", button(t, "lin", "Linux · Steam Deck", "One Terminal line"))
    print(f"wrote {len(made)} files to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
