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
