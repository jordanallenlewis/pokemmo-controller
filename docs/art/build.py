"""Writes the README's banner pictures (hero, install steps, feature cards, install buttons,
at-a-glance strip) as SVG, in a light and a dark variant.

    python docs/art/build.py          rewrite docs/img/*.svg

Same look as the website (pokemmocontroller.com): the colours come from
brand/tokens.json (site/styles.css is checked against it), and the logo, the PokeMMO
wordmark and the feature icons are read from site/ so they cannot drift. These are text
banners only. The one controller shown (the hero) is the real photo the website uses;
nothing here draws a controller or a wheel. The controller maps and the wheel picture are
rendered from the photos and the layout by docs/art/render.py. Standard library only.
"""
import base64
import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "img"
TOKENS = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))
_d, _l = TOKENS["dark"], TOKENS["light"]
# Fonts come from brand/tokens.json too: display (headings, weight 700+) is Bricolage Grotesque, text and
# labels are Geist, the domain is Geist Mono. GitHub cannot load web fonts for an image, so the font files are
# embedded in every picture as data (only the faces that picture uses).
FONT = TOKENS["type"]["text"]
SCALE = TOKENS["scale"]
FACES = TOKENS["faces"]


def _face_css(kind):
    f = FACES[kind]
    data = base64.b64encode((ROOT / f["file"]).read_bytes()).decode("ascii")
    return (f'@font-face{{font-family:"{f["family"]}";font-weight:{f["weight"]};font-style:normal;'
            f'src:url(data:font/woff2;base64,{data}) format("woff2")}}')


def with_fonts(doc):
    """Set the display font on heavy text, the text font on the rest, and embed the files that are used."""
    doc = re.sub(r'<text ((?:(?!>)[^>])*font-weight="[78]\d\d"[^>]*)>', r'<text class="d" \1>', doc)
    used = ["display"] if 'class="d"' in doc else []
    if re.search(r'<text (?!class="d")', doc):
        used.append("text")
    if 'class="m"' in doc:
        used.append("mono")
    style = ("<style>text{font-family:%s}.d{font-family:%s}.m{font-family:%s}%s</style>"
             % (TOKENS["type"]["text"].replace('"', "'"), TOKENS["type"]["display"].replace('"', "'"),
                TOKENS["type"]["mono"].replace('"', "'"), "".join(_face_css(k) for k in used)))
    head = doc.index(">") + 1
    return doc[:head] + "\n" + style + doc[head:]

# Base colours come from brand/tokens.json (the one source, shared with the site and the app);
# the lines and body shades are the picture-only tints worked out from them.
THEMES = {
    "light": dict(bg=_l["bg"], card=_l["surface"], ink=_l["ink"], mute=_l["muted"], line="#ddd8cb",
                  body="#e7e3d9", body2="#d9d4c7", edge="#b4ae9e", accent=_l["accent-text"], fill=_l["accent"],
                  on=_l["accent-ink"], soft="#fbefc9", amber=_l["accent"], dim="#b4ae9e", screen="#1b1e24", glow="#ece6d6"),
    "dark": dict(bg=_d["bg"], card=_d["surface"], ink=_d["ink"], mute=_d["muted"], line="#2f333b",
                 body=_d["surface2"], body2="#30353d", edge="#4a505c", accent=_d["accent-text"],
                 fill=_d["accent"], on=_d["accent-ink"], soft="#34301f", amber=_d["accent"],
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


def svg(w, h, t, body, title, desc=""):
    c = THEMES[t]
    return with_fonts(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d">\n'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc or title)}</desc>\n'
            f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>\n{body}\n</svg>\n')


def text(x, y, s, size, fill, weight=400, anchor="start", extra=""):
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" {extra}>{esc(s)}</text>')


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
        body += text(x + 112, 119, h, 34, c["ink"], 800)
        for j, ln in enumerate(wrap(d, 34)):
            body += text(x + 36, 178 + j * 34, ln, 24, c["mute"])
        if i < 2:
            body += f'<path d="M {x+cw+8},180 l 28,0 m -10,-10 l 10,10 l -10,10" fill="none" stroke="{c["accent"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    return svg(W, H, t, body, "Install in three steps", "Close PokeMMO, paste one line for your system, play from Steam.")


def steps_phone(t):
    c = THEMES[t]
    W, ch, gap = 900, 268, 26
    body = ""
    for i, (n, h, d) in enumerate(STEPS):
        y = 30 + i * (ch + gap)
        body += f'<rect x="30" y="{y}" width="{W-60}" height="{ch}" rx="24" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
        body += f'<circle cx="104" cy="{y+68}" r="38" fill="{c["fill"]}"/>' + text(104, y + 82, n, 42, c["on"], 800, "middle")
        body += text(166, y + 82, h, 48, c["ink"], 800)
        for j, ln in enumerate(wrap(d, 38)):
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
    W, cw, ch, gap = 1600, 755, 244, 30
    body = ""
    for i, (h, d) in enumerate(FEATURES):
        x, y = 30 + (i % 2) * (cw + gap), 30 + (i // 2) * (ch + gap)
        body += f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="22" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2.5"/>'
        body += f'<rect x="{x+30}" y="{y+34}" width="92" height="92" rx="22" fill="{c["soft"]}"/>' + icon(c, i, x + 44, y + 48)
        body += text(x + 152, y + 62, h, 32, c["ink"], 800)
        for j, ln in enumerate(wrap(d, 42)):
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
        for j, ln in enumerate(wrap(d, 38)):
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


def photo(x, y, w):
    """The real Xbox controller photo (docs/xbox-controller.webp, the one the website uses), embedded."""
    import base64
    raw = (ROOT / "docs" / "xbox-controller.webp").read_bytes()
    pw, ph = 1800, 1303      # its size: site/data/hotspots.json "xbox"
    return (f'<image x="{x}" y="{y}" width="{w}" height="{w * ph / pw:g}" '
            f'href="data:image/webp;base64,{base64.b64encode(raw).decode()}"/>')


HERO_ALT = "PokeMMO Controller: play PokeMMO from the couch with an Xbox, PlayStation or Switch Pro controller"


def hero(t):
    """The website's hero. The banner is the site's dark ink in both variants, like the logo."""
    c = THEMES["dark"]
    W, H = 1600, 690
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="36" fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="4"/>'
    body += f'<circle cx="1290" cy="340" r="240" fill="{c["glow"]}"/>'
    body += photo(960, 150, 640)
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
    body = f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="40" fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="4"/>'
    body += f'<circle cx="450" cy="930" r="230" fill="{c["glow"]}"/>'
    body += photo(160, 720, 580)
    body += logo_mark(56, 56, 60)
    body += (f'<text x="{56 + 60 * 420 / 222 + 20:g}" y="100" font-size="38" font-weight="700" fill="{c["ink"]}">PokeMMO '
             f'<tspan fill="{c["accent"]}">Controller</tspan></text>')
    body += text(56, 222, "FREE · OPEN SOURCE", 26, c["mute"], 500, extra='letter-spacing="3"')
    body += text(56, 318, "Play", 104, c["ink"], 800) + wordmark(282, 254, 64)
    body += text(56, 424, "from the couch", 104, c["ink"], 800)
    body += text(56, 500, "Every action on your controller:", 32, c["mute"], 400)
    body += text(56, 544, "battles, hotbar, Bag, GTL, Pokédex.", 32, c["mute"], 400)
    body += text(56, 588, "One command to install.", 32, c["mute"], 400)
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
        body += text(x, y, n, 74, c["accent"], 800, "middle") + text(x, y + 50, d, 28, c["mute"], 500, "middle")
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
    return with_fonts(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                      f'aria-label="{esc(title)}">{body}</svg>\n')


def og():
    """The social card (link previews): the hero on a 1.91:1 canvas. Rasterised to site/assets/og.png by docs/art/raster.js."""
    c = THEMES["dark"]
    W, H = 1600, 840
    T = TOKENS["terms"]
    body = f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>'
    body += f'<circle cx="1270" cy="440" r="280" fill="{c["glow"]}"/>'
    body += photo(900, 200, 640)
    body += logo_mark(80, 70, 64)
    body += (f'<text x="{80 + 64 * 420 / 222 + 22:g}" y="116" font-size="40" font-weight="700" fill="{c["ink"]}">PokeMMO '
             f'<tspan fill="{c["accent"]}">Controller</tspan></text>')
    body += text(80, 360, T["tagline"][0].split()[0], 104, c["ink"], 800) + wordmark(296, 292, 64)
    body += text(80, 480, T["tagline"][1], 104, c["ink"], 800)
    body += text(80, 560, "Free and open source. One command to install.", 28, c["mute"], 400)
    body += chips(c, 80, 616, T["platforms"][:3], 22, 22, 42)
    body += text(80, 740, T["domain"], 34, c["accent"], 500, extra='class="m"')
    return with_fonts(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                      f'aria-label="{esc(HERO_ALT)}"><title>{esc(T["product"])}</title>{body}</svg>\n')


SOCIAL = ROOT / "site" / "assets" / "og.svg"


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
        put("get-windows", button(t, "win", "Windows", "One PowerShell line"))
        put("get-mac", button(t, "mac", "macOS", "One Terminal line"))
        put("get-linux", button(t, "lin", "Linux · Steam Deck", "One Terminal line"))
    if not out:
        with open(SOCIAL, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(og())
    print(f"wrote {len(made)} files to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
