# Contributing

Thanks for helping. Bug reports and ideas go in [Issues](https://github.com/jordanallenlewis/pokemmo-controller/issues); the forms ask for your system and controller, which is most of what is needed.

## Code

- Fork, make a branch, open a pull request against `main`. Keep each pull request to one change.
- Run the tests: `python -m pytest`. They run on Windows, macOS and Linux for every pull request.
- The layout follows PokeMMO's rules: one input does one action, and nothing here sends a keypress for you, so no macros, turbo or sequences. A change that needs any of those will not be merged.
- `tools/layout.py` is the single source for the layout: the actions, the default binds, the wheel slices and what each button is printed as on each controller. Nothing restates them by hand. After changing any of it, run `python site/build.py` (writes the website data and the README tables) and, for the pictures, `python docs/art/render.py` (needs Node and Playwright; screenshots the website's own map). The tests fail when a generated copy or a picture is stale.
- Controller pictures are only ever the real photos (`site/assets/`, `docs/xbox-controller.webp`) with the hotspots in `site/data/hotspots.json`. Do not draw or generate a controller or wheel diagram.
- Website changes live in `site/` and publish to [pokemmocontroller.com](https://pokemmocontroller.com) when merged to `main`.

## Standing rules

These two apply to every change, and a pull request that breaks one is not merged.

### Everything adapts live to the screen

Everything the tool draws (the app window, the wheel on the Steam Input overlay, on-screen hints) follows the screen as it changes, with no restart: window resizes, fullscreen and windowed switches, a different monitor, docking or undocking a Steam Deck, and any resolution, aspect ratio or scale.

- Ratios to hold: 16:9, 16:10 (Steam Deck), 21:9 and 32:9 ultrawide, 4:3, portrait. Sizes: 720p up to 4K and 5K. System scaling: 100% to 300%.
- Listen for the change (resize, display and scale events) instead of measuring once at start. Size from the game window and the viewport, never from fixed pixels. Text stays readable and is never clipped; the wheel stays centred and in proportion.
- Test it: the tests and CI run the app page and the wheel at each ratio and scale, with screenshots, and a person checks real devices. A claim for a device nobody tested says "unverified".
- Steam draws its wheel in screen pixels, so the wheel follows a changed screen by the tool re-reading the game window and rewriting it while the tool runs; anything that cannot follow live is written down in the docs rather than hidden.

### One canon for fonts, sizes, images and words

Fonts, type sizes, colours, images and terms come from `brand/` ([brand/CANON.md](brand/CANON.md)) and are never copied: the app and website use the tokens, the README and docs show only images from `brand/images.json`, and command-line text, wheel labels and docs use the names in `brand/glossary.json` and `tools/layout.py`. `python brand/check.py` (run by the tests) fails on a non-canonical word, font, size or image. To add one, add it to the source first, in the same pull request.

## Release notes

Each release's notes say what a player can now do or what was fixed, in plain words, with the system it affects. Install steps are not repeated there; they live on the website.
