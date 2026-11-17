# Website handoff (pokemmocontroller.com)

Built in a Claude session on ax1, 2026-11-17, at Jordan's ask; now owned by Maya (hq-builder), who may delegate day-to-day work to Jules (hq-pokemmo).

## State
- Live: https://jordanallenlewis.github.io/pokemmo-controller/ (GitHub Pages, workflow `.github/workflows/site.yml`, deploys on push to main touching `site/**` or `tools/layout.py`).
- Domain: pokemmocontroller.com, registered at Cloudflare 2026-11-17 ($11.17/yr, auto-renew, privacy). Nameservers ignat/megan.ns.cloudflare.com. GitHub Pages custom domain is already set to `pokemmocontroller.com`.
- Site: plain HTML/CSS/JS in `site/` (see `site/README.md`). Button map + wheel come from `tools/layout.py` via `python site/build.py` (CI checks it).

## Left to do
1. DNS in the Cloudflare zone: CNAME `@` -> `jordanallenlewis.github.io` and CNAME `www` -> `jordanallenlewis.github.io`, both DNS only (grey cloud).
2. When GitHub shows the domain verified and the certificate issued: `gh api -X PUT repos/jordanallenlewis/pokemmo-controller/pages -F https_enforced=true`. Check https://pokemmocontroller.com and https://www.pokemmocontroller.com load.
3. Point README, the repo "website" field and future Reddit drafts at https://pokemmocontroller.com.

5. Legion Go S tab in the button map once Jordan sends a front photo of his device (no free-licence photo exists).
6. Keep the site in step with releases: View = map, top wheel slice = do nothing, Focus Ring on LB once those PRs ship (rebuild `site/data/layout.json`, update captions).

## How it was made
- Logo: PMC (PM white, C yellow = the controller), original pixel lettering from `site/logo/make.py`; exports in `site/assets/brand/`.
- Hero word "PokeMMO" uses PokeMMO's own wordmark (`assets/pokemmo-wordmark.svg`, traced from pokemmo.com). Footer says not affiliated; swap to text if PokeMMO asks.
- Controller photos: Wikimedia Commons (credits in the footer), backgrounds removed.

- Design: unslop + design-taste-frontend passes; one accent (PMC yellow), no glows/floating loops, keycap labels.
- Public repo: no AI attribution anywhere.

## Undo
- Site: revert the site PRs (#31-#34); disable Pages in repo settings.
- Domain: Cloudflare dashboard (turn auto-renew off).
