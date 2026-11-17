# Contributing

Thanks for helping. Bug reports and ideas go in [Issues](https://github.com/jordanallenlewis/pokemmo-controller/issues); the forms ask for your system and controller, which is most of what is needed.

## Code

- Fork, make a branch, open a pull request against `main`. Keep each pull request to one change.
- Run the tests: `python -m pytest`. They run on Windows, macOS and Linux for every pull request.
- The layout follows PokeMMO's rules: one input does one action, and nothing here sends a keypress for you, so no macros, turbo or sequences. A change that needs any of those will not be merged.
- `tools/layout.py` is the single source for the layout: the actions, the default binds, the wheel slices and what each button is printed as on each controller. Nothing restates them by hand. After changing any of it, run `python site/build.py` (writes the website data and the README tables) and, for the pictures, `python docs/art/render.py` (needs Node and Playwright; screenshots the website's own map). The tests fail when a generated copy or a picture is stale.
- Controller pictures are only ever the real photos (`site/assets/`, `docs/xbox-controller.webp`) with the hotspots in `site/data/hotspots.json`. Do not draw or generate a controller or wheel diagram.
- Website changes live in `site/` and publish to [pokemmocontroller.com](https://pokemmocontroller.com) when merged to `main`.

## Release notes

Each release's notes say what a player can now do or what was fixed, in plain words, with the system it affects. Install steps are not repeated there; they live on the website.
