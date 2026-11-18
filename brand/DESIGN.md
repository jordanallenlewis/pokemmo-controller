# Design rules

One source: `tokens.json`. `python brand/build.py` writes `tokens.css` and puts the
same values into the remap page; a test compares the site's dark values.

- **Ink and one accent.** Dark ink surfaces, warm off-white text, one yellow (`--accent`) for the thing to press next and for "selected". Status uses green, amber, red, never the accent.
- **Light theme follows the system.** Same layout; the accent button keeps dark text; accent text on light is the darker `--accent-text`.
- **The controller is the centrepiece.** Remap by clicking a button on the picture. The wheel is drawn with the same strokes, fills and accent.
- **Type.** Display and text fonts are used if installed, with system fonts as the fallback. Nothing is downloaded: the app works offline and sends nothing anywhere.
- **Sizes in rem** so text scales with the player's setting. SVG labels scale with the picture.
- **Focus is always visible** (accent ring). Everything clickable on the picture is also reachable with the keyboard.
- **Motion** is short (150 ms) and off under reduced motion.
- **Mark.** `mark.svg`: the PMC pixel lettering in a ring. Keep clear space of a quarter of its width.

## The accent (decided 2026-11-18)

The primary colour is **#F0EA6B**, the yellow in PokeMMO's own logo (sampled from the logo on pokemmo.com; the colour only, never the logo). Every accent in the site, the app, the wheel, the README pictures and the icons comes from `tokens.json`.

| Token | Value | Rule |
|---|---|---|
| `accent` | `#f0ea6b` | fills, rings, selected state; on dark surfaces also text (14.7:1 on `#121418`) |
| `accent-ink` | `#1a1408` | text on an accent fill (14.5:1) |
| `accent-hover` | `#f5f199` | hover and pressed fill: the accent with HSL lightness raised 8 points |
| `accent-edge` | `#a8a10b` | 1px edge and the shadow under outlined logo letters: HSL lightness 35 |
| `accent-text` (light theme) | `#635f03` | accent as text on a light surface (6.0:1 on `#f6f4ef`). The plain accent is 1.26:1 on white: **never use it as text or a line on light**, only as a fill with `accent-ink` on it |
| `accent-soft` | accent at 14% (dark) / 28% (light) | hover wash |

Status colours (ok, bad, warn) are separate and never the accent. No hard-coded yellow outside `tokens.json` and the files generated from it; `tests/test_brand.py` fails if the old amber or any stray accent value comes back.
