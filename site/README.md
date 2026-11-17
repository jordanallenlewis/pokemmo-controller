# pokemmocontroller.com

The one-page website for this project. Plain HTML, CSS and JavaScript: no framework, no build step beyond one data file.

- `index.html`, `styles.css`, `app.js`: the page.
- `data/layout.json`: the button map and wheel, generated from `tools/layout.py` by `python site/build.py`. Run it after changing the default layout; CI fails if it is out of date.
- `assets/`: an in-game screenshot, the icon and the social preview image. The controller photo ("Xbox Series Controller Carbon Black" by UKER, CC BY-SA 4.0, background removed) and the remap screenshot come from `docs/` (one copy in the repo); the workflow and `dev.py` serve them as `assets/controller.webp` and `assets/remap-screen.png`.
- `dev.py`: local preview that reloads on save: `python site/dev.py` then open http://127.0.0.1:8790/.

Published by `.github/workflows/site.yml` to GitHub Pages on every push to `main` that touches the site or the layout.
