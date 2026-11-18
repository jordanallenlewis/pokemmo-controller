"""Generates the PokeMMO Controller logo concepts as SVG from an original pixel font.
Standard library only.  python site/logo/make.py"""
import os
OUT = os.path.dirname(os.path.abspath(__file__))
# Original 5x7 pixel glyphs (chunky, squared corners).
G = {
 "P": ["1111.","11.11","11.11","1111.","11...","11...","11..."],
 "O": [".111.","11.11","11.11","11.11","11.11","11.11",".111."],
 "K": ["11.11","11.11","1111.","111..","1111.","11.11","11.11"],
 "E": ["11111","11...","11...","1111.","11...","11...","11111"],
 "M": ["11...11","111.111","1111111","11.1.11","11...11","11...11","11...11"],
 "C": [".1111","11...","11...","11...","11...","11...",".1111"],
 "N": ["11..11","111.11","111111","11.111","11..11","11..11","11..11"],
 "T": ["11111","..1..","..1..","..1..","..1..","..1..","..1.."],
 "R": ["1111.","11.11","11.11","1111.","11.1.","11.11","11.11"],
 "L": ["11...","11...","11...","11...","11...","11...","11111"],
}
def word(text, x, y, px, gap=1):
    rects = []
    for ch in text:
        if ch == " ":
            x += 3 * px; continue
        for r, row in enumerate(G[ch]):
            for c, v in enumerate(row):
                if v == "1":
                    rects.append((x + c * px, y + r * px, px))
        x += (len(G[ch][0]) + gap) * px
    return rects, x
def path(rects):
    return "".join(f"M{x} {y}h{s}v{s}h-{s}z" for x, y, s in rects)
SHADE = {"#f4f1ea": "#9aa0ab", "#f0ea6b": "#a8a10b", "#a3a8b3": "#5d636e"}
def outlined(rects, fill, stroke, sw):
    d = path(rects)
    off = max(2, rects[0][2] // 3) if rects else 2
    ds = "".join(f"M{x+off} {y+off}h{s}v{s}h-{s}z" for x, y, s in rects)
    return (f'<path d="{d}{ds}" fill="{stroke}" stroke="{stroke}" stroke-width="{sw*2}" stroke-linejoin="miter"/>'
            f'<path d="{ds}" fill="{SHADE.get(fill, stroke)}"/>'
            f'<path d="{d}" fill="{fill}"/>')
# pixel gamepad icon on a 16x10 grid
PAD = ["..11111111111...",".1111111111111..","111.111111.1111.","1...1111111.1.11","111.11111111.111",
       "1111111111111111","1111111..1111111","111111....111111","11111......11111",".111........111."]
def pad(x, y, px, body, hole="#121418"):
    out = []
    for r, row in enumerate(PAD):
        for c, v in enumerate(row):
            if v == "1": out.append((x + c * px, y + r * px, px))
    return f'<path d="{path(out)}" fill="{body}"/>'
WHITE, YEL, INK, BG = "#f4f1ea", "#f0ea6b", "#121418", "#121418"

def concept1():  # stacked wordmark, PokeMMO-style two tone with outline
    a, w1 = word("POKE", 20, 20, 12); b, w2 = word("MMO", w1 + 6, 20, 12)
    c, w3 = word("CONTROLLER", 22, 128, 6)
    W = max(w2, w3) + 20
    s = outlined(a, WHITE, INK, 5) + outlined(b, YEL, INK, 5) + outlined(c, WHITE, INK, 3)
    return W, 190, s
def concept2():  # app icon: pixel pad, yellow on dark tile
    s = f'<rect width="256" height="256" rx="56" fill="{BG}"/>' + pad(32, 68, 12, YEL)
    s += f'<rect x="88" y="104" width="12" height="36" fill="{BG}"/><rect x="76" y="116" width="36" height="12" fill="{BG}"/>'
    s += f'<rect x="164" y="104" width="12" height="12" fill="{BG}"/><rect x="188" y="116" width="12" height="12" fill="{BG}"/>'
    return 256, 256, s
def concept3():  # icon + horizontal wordmark
    s = pad(10, 22, 7, YEL)
    a, w1 = word("POKE", 140, 18, 8); b, w2 = word("MMO", w1 + 4, 18, 8)
    c, w3 = word("CONTROLLER", 141, 92, 4)
    s += outlined(a, WHITE, INK, 4) + outlined(b, YEL, INK, 4) + outlined(c, "#a3a8b3", INK, 2)
    return max(w2, w3) + 14, 136, s
def concept4():  # badge monogram PMC
    a, w1 = word("P", 40, 64, 18); b, w2 = word("MC", w1 + 6, 64, 18)
    s = f'<rect x="8" y="8" width="{w2+24}" height="{64+7*18+56}" rx="40" fill="{BG}" stroke="{YEL}" stroke-width="8"/>'
    s += outlined(a, WHITE, INK, 6) + outlined(b, YEL, INK, 6)
    return w2 + 40, 64 + 7 * 18 + 72, s
for i, f in enumerate((concept1, concept2, concept3, concept4), 1):
    W, H, body = f()
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" shape-rendering="crispEdges">{body}</svg>'
    open(os.path.join(OUT, f"concept-{i}.svg"), "w").write(svg)
print("ok")

# ---- PMC refinements ----
def pmc_letters(x, y, px, out):
    # PM white, C yellow: the C is the controller, which is what the project is about.
    a, w1 = word("PM", x, y, px); b, w2 = word("C", w1 + px // 2, y, px)
    return outlined(a, WHITE, INK, out) + outlined(b, YEL, INK, out), w2
def r1():  # rounded badge, tighter, yellow ring
    body, w = pmc_letters(44, 46, 16, 5)
    W, H = w + 36, 46 + 7 * 16 + 52
    return W, H, f'<rect x="6" y="6" width="{W-12}" height="{H-12}" rx="34" fill="{BG}" stroke="{YEL}" stroke-width="10"/>' + body
def r2():  # controller-shaped badge: PMC inside a pad silhouette
    px = 14
    rows = ["...1111111111111111111...", "..111111111111111111111..", ".11111111111111111111111.",
            "1111111111111111111111111", "1111111111111111111111111", "1111111111111111111111111",
            "1111111111111111111111111", "1111111111111111111111111", "1111111111111111111111111",
            "1111111111111111111111111", "11111111.........11111111", "1111111...........1111111",
            ".11111.............11111."]
    r = [(c * px, rr * px, px) for rr, row in enumerate(rows) for c, v in enumerate(row) if v == "1"]
    body, w = pmc_letters(2 * px + 10, 2 * px, 13, 4)
    on = {(rr, c) for rr, row in enumerate(rows) for c, v in enumerate(row) if v == "1"}
    inner = [(c * px, rr * px, px) for (rr, c) in on if all((rr + a, c + b) in on for a in (-1, 0, 1) for b in (-1, 0, 1))]
    shell = f'<path d="{path(r)}" fill="{YEL}"/><path d="{path(inner)}" fill="{BG}"/>'
    return 25 * px, 13 * px, shell + body
def r3():  # lockup: PMC badge + small wordmark
    W1, H1, b = r1()
    a, w1 = word("POKEMMO", W1 + 28, 52, 6); c, w2 = word("CONTROLLER", W1 + 28, 112, 6)
    s = f'<g>{b}</g>' + outlined(a, WHITE, INK, 3) + outlined(c, YEL, INK, 3)
    return max(w1, w2) + 16, H1, s
def r4():  # square app icon: PM over C? keep PMC on one line, square tile
    body, w = pmc_letters(0, 0, 10, 4)
    x0 = (256 - w) // 2; y0 = (256 - 70) // 2
    body, w = pmc_letters(x0, y0, 10, 4)
    return 256, 256, f'<rect width="256" height="256" rx="56" fill="{BG}"/><rect x="10" y="10" width="236" height="236" rx="48" fill="none" stroke="{YEL}" stroke-width="8"/>' + body
for i, f in enumerate((r1, r2, r3, r4), 1):
    W, H, body = f()
    open(os.path.join(OUT, f"pmc-{i}.svg"), "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 {W+12} {H+12}" shape-rendering="crispEdges">{body}</svg>')
