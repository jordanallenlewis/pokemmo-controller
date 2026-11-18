// Rasterises the social card (site/assets/og.svg) to site/assets/og.png at 2400 x 1260 (1.5x its 1600 x 840 canvas),
// so link previews are sharp on high-density screens. The SVG carries its own fonts, so nothing else is needed.
//   node raster.js <og.svg> <og.png>
const { chromium } = require("playwright");
const [src, out] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1600, height: 840 }, deviceScaleFactor: 1.5 });
  const page = await ctx.newPage();
  await page.goto("file://" + require("path").resolve(src));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out });
  await b.close();
})();
