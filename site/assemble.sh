#!/usr/bin/env bash
# Assemble the published files into $1 (default _site). Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-_site}"
rm -rf "$out"; mkdir -p "$out"
cp -r site/index.html site/styles.css site/app.js site/CNAME site/robots.txt site/sitemap.xml site/404.html site/assets site/data "$out"/
cp docs/xbox-controller.webp "$out/assets/controller.webp"
cp docs/remap-screen.png "$out/assets/remap-screen.png"
touch "$out/.nojekyll"
