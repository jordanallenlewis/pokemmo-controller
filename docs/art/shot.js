// Screenshots the website's own button map and wheel, light and dark, for the README.
// Called by docs/art/render.py:  node shot.js <site url> <out dir> <tokens.json>
// The page, photos, hotspots and names are the site's; this only picks the pad, sets the theme,
// joins each listed button to its place on the photo with a thin line, and takes the picture.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [url, out, tokensFile] = process.argv.slice(2);
const T = JSON.parse(fs.readFileSync(tokensFile, "utf8"));
const WIDTH = 1200, SCALE = 3.2;            // 1200 css px x 3.2 = 3840 px wide
const KINDS = ["xbox", "playstation", "switch", "deck"];

const css = (t) => {
  const c = T[t];
  return `
  :root { --bg:${c.bg}; --bg-2:${c.bg2}; --surface:${c.surface}; --surface-2:${c.surface2}; --line:${c.line};
    --ink:${c.ink}; --muted:${c.muted}; --dim:${c.dim}; --yellow:${c.accent}; --yellow-ink:${c["accent-ink"]};
    --accent-soft:${c["accent-soft"]}; color-scheme:${t}; }
  .map { width:${WIDTH}px !important; max-width:none !important; margin:0 !important; border-radius:0 !important; border:0 !important; position:relative; }
  .map .seg { display:none !important; }
  .nav, .sec-head { display:none !important; }
  .pad .pill rect { fill:${c.surface2} !important; stroke:${t === "dark" ? "#3a3f49" : "#b8b3a6"} !important; }
  .pad .pill-t { fill:${c.muted} !important; }
  .pad-lg .ring { stroke:${t === "dark" ? "rgba(255,255,255,.34)" : "rgba(20,22,26,.42)"} !important; stroke-width:5 !important; }
  .binds .key { background:${c.surface2} !important; color:${c.ink} !important; border-color:${t === "dark" ? "rgba(244,241,234,.14)" : "rgba(20,22,26,.2)"} !important; }
  .binds li, .binds li.on { background:transparent !important; }
  .binds .act { color:${c.ink}; font-size:16px !important; }
  .pad image { filter:${t === "dark" ? "drop-shadow(0 30px 40px rgba(0,0,0,.6))" : "drop-shadow(0 24px 30px rgba(20,22,26,.22))"} !important; }`;
};

(async () => {
  const browser = await chromium.launch();
  fs.mkdirSync(out, { recursive: true });
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport: { width: WIDTH + 200, height: 1000 }, deviceScaleFactor: SCALE, colorScheme: theme, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: css(theme) });
    await page.evaluate(() => document.fonts.ready);
    for (const kind of KINDS) {
      await page.evaluate((k) => document.querySelector(`[data-pad-kind="${k}"]`).click(), kind);
      await page.waitForFunction((k) => document.querySelector('[data-pad="map"] svg')?.getAttribute("aria-label") && document.querySelectorAll(".binds li").length > 0, kind);
      await page.waitForTimeout(300);
      // join each listed button to its place on the photo
      await page.evaluate(({ c, dark }) => {
        const map = document.querySelector(".map");
        map.querySelectorAll(".leads").forEach((n) => n.remove());
        const mr = map.getBoundingClientRect();
        const NS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(NS, "svg");
        svg.setAttribute("class", "leads");
        svg.setAttribute("style", `position:absolute;left:0;top:0;width:${mr.width}px;height:${mr.height}px;pointer-events:none;overflow:visible`);
        const seen = {};
        for (const li of map.querySelectorAll(".binds li")) {
          const id = li.dataset.id, base = id.replace("_click", "");
          const g = map.querySelector(`.pad .ctl[data-id="${base}"]`);
          if (!g) continue;
          const part = g.querySelector(".ring, rect");
          const pr = part.getBoundingClientRect(), lr = li.getBoundingClientRect();
          const left = lr.left + lr.width / 2 < mr.left + mr.width / 2;
          const n = (seen[base] = (seen[base] || 0) + 1) - 1;
          const k = li.querySelector(".key").getBoundingClientRect();
          const x0 = (left ? lr.right : lr.left) - mr.left, y0 = lr.top + lr.height / 2 - mr.top;
          const pill = g.classList.contains("pill");
          let x1 = (pill ? (left ? pr.left : pr.right) : pr.left + pr.width / 2) - mr.left, y1 = pr.top + pr.height / 2 - mr.top + (n ? 18 : 0);
          x1 += n ? (left ? -12 : 12) : 0;
          const x2 = x0 + (left ? 28 : -28);
          const ln = document.createElementNS(NS, "polyline");
          ln.setAttribute("points", `${x0},${y0} ${x2},${y0} ${x1},${y1}`);
          ln.setAttribute("fill", "none"); ln.setAttribute("stroke", c.accentLine); ln.setAttribute("stroke-width", "1.6"); ln.setAttribute("stroke-linejoin", "round");
          const dot = document.createElementNS(NS, "circle");
          dot.setAttribute("cx", x1); dot.setAttribute("cy", y1); dot.setAttribute("r", 5);
          dot.setAttribute("fill", c.accentLine); dot.setAttribute("stroke", c.bg); dot.setAttribute("stroke-width", "2");
          svg.append(ln, dot);
        }
        map.append(svg);
      }, { c: { accentLine: theme === "dark" ? "#ffc833" : "#b07a00", bg: T[theme].surface }, dark: theme === "dark" });
      await page.locator(".map").screenshot({ path: path.join(out, `map-${kind}-${theme}.png`) });
    }
    // the wheel
    await page.evaluate(() => { document.querySelector("#wheel").scrollIntoView(); });
    await page.addStyleTag({ content: `
      .wheel-fig { width:1200px !important; max-width:none !important; margin:0 !important; padding:60px; background:${T[theme].surface}; }
      .wheel-fig figcaption { display:none !important; }
      .wheel .slice { transition:none !important; }
      .wheel .slice path { fill:${T[theme].surface2} !important; stroke:${theme === "dark" ? T[theme].bg2 : T[theme].surface} !important; stroke-width:5 !important; }
      .wheel .slice.top path { fill:${T[theme].bg2} !important; }
      .wheel .slice.on path { fill:${T[theme].surface2} !important; }
      .wheel .slice text { fill:${T[theme].ink} !important; }
      .wheel .slice .k { fill:${T[theme]["accent-text"]} !important; }
      .wheel .hub { fill:${T[theme].bg} !important; }
      .wheel .hub-t { fill:${T[theme].muted} !important; }` });
    await page.evaluate(() => document.querySelectorAll(".wheel .slice").forEach((g) => g.classList.remove("on")));
    await page.locator(".wheel-fig").screenshot({ path: path.join(out, `wheel-${theme}.png`) });
    await ctx.close();
  }
  await browser.close();
})();
