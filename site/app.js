// PokeMMO Controller site. No dependencies. Layout data comes from data/layout.json,
// which site/build.py writes from tools/layout.py (the same layout the installer puts on).
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // One photo per controller, with hotspots in that photo's pixels. Positions follow the
  // button's place on the pad (a = bottom face button), like the layout itself.
  const PILLS = (W, xl, xr) => {
    const w = W * 0.12, gap = W * 0.06;
    return { lb: { pill: true, x: xl, y: -gap, w }, rb: { pill: true, x: xr, y: -gap, w },
             lt: { pill: true, x: xl, y: -gap * 2.4, w }, rt: { pill: true, x: xr, y: -gap * 2.4, w } };
  };
  const MODELS = {
    xbox: { img: "assets/controller.webp", w: 1800, h: 1303, alt: "Xbox controller", spots: {
      ls: { x: 435, y: 345, r: 120 }, rs: { x: 1257, y: 630, r: 112 }, view: { x: 810, y: 348, r: 46 }, menu: { x: 1100, y: 348, r: 46 },
      y: { x: 1437, y: 228, r: 58 }, x: { x: 1323, y: 353, r: 58 }, b: { x: 1565, y: 365, r: 58 }, a: { x: 1463, y: 480, r: 58 },
      dup: { x: 698, y: 598, r: 46 }, ddown: { x: 698, y: 770, r: 46 }, dleft: { x: 606, y: 683, r: 46 }, dright: { x: 792, y: 683, r: 46 },
      ...PILLS(1800, 430, 1370) } },
    playstation: { img: "assets/ps5.webp", w: 1799, h: 1266, alt: "PlayStation DualSense controller", spots: {
      ls: { x: 652, y: 488, r: 112 }, rs: { x: 1213, y: 488, r: 112 }, view: { x: 495, y: 95, r: 40 }, menu: { x: 1322, y: 95, r: 40 },
      y: { x: 1467, y: 155, r: 62 }, x: { x: 1340, y: 272, r: 62 }, b: { x: 1597, y: 272, r: 62 }, a: { x: 1477, y: 397, r: 62 },
      dup: { x: 363, y: 180, r: 48 }, ddown: { x: 375, y: 358, r: 48 }, dleft: { x: 270, y: 268, r: 48 }, dright: { x: 455, y: 262, r: 48 },
      ...PILLS(1799, 330, 1470) } },
    switch: { img: "assets/switch.webp", w: 1526, h: 1233, alt: "Nintendo Switch Pro Controller", spots: {
      ls: { x: 465, y: 185, r: 98 }, rs: { x: 998, y: 440, r: 98 }, view: { x: 713, y: 135, r: 38 }, menu: { x: 1070, y: 205, r: 38 },
      y: { x: 1278, y: 248, r: 58 }, x: { x: 1138, y: 308, r: 58 }, b: { x: 1370, y: 357, r: 58 }, a: { x: 1228, y: 415, r: 58 },
      dup: { x: 590, y: 330, r: 40 }, ddown: { x: 555, y: 455, r: 40 }, dleft: { x: 500, y: 375, r: 40 }, dright: { x: 648, y: 395, r: 40 },
      ...PILLS(1526, 400, 1250) } },
    deck: { img: "assets/deck.webp", w: 1244, h: 462, alt: "Steam Deck", spots: {
      ls: { x: 198, y: 83, r: 46 }, rs: { x: 1040, y: 72, r: 46 }, view: { x: 158, y: 28, r: 15 }, menu: { x: 1092, y: 12, r: 15 },
      y: { x: 1163, y: 22, r: 21 }, x: { x: 1128, y: 55, r: 21 }, b: { x: 1205, y: 55, r: 21 }, a: { x: 1168, y: 88, r: 21 },
      dup: { x: 90, y: 45, r: 18 }, ddown: { x: 90, y: 100, r: 18 }, dleft: { x: 62, y: 72, r: 18 }, dright: { x: 118, y: 72, r: 18 },
      ...PILLS(1244, 160, 1080) } },
  };
  const ORDER_LEFT = ["lt", "lb", "ls", "ls_click", "view", "dup", "dright", "ddown", "dleft"];
  const ORDER_RIGHT = ["rt", "rb", "y", "x", "b", "a", "menu", "rs", "rs_click"];
  const TICKER = ["rb", "a", "menu", "dup", "rt", "view", "b", "lb", "y", "ls_click"];

  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };

  function padSvg(kind, interactive) {
    const m = MODELS[kind], top = m.w * 0.06 * 2.4 + m.w * 0.04, sw = m.w / 300;
    const svg = el("svg", { viewBox: `0 ${-top} ${m.w} ${m.h + top}`, role: "img", "aria-label": m.alt });
    const fid = `gl-${kind}-${interactive ? "m" : "h"}`;
    const f = el("filter", { id: fid, x: "-50%", y: "-50%", width: "200%", height: "200%" }, el("defs", {}, svg));
    el("feGaussianBlur", { stdDeviation: String(sw * 1.7) }, f);
    el("image", { href: m.img, x: 0, y: 0, width: m.w, height: m.h }, svg);
    for (const [id, s] of Object.entries(m.spots)) {
      const g = el("g", { class: "ctl" + (s.pill ? " pill" : ""), "data-id": id }, svg);
      if (s.pill) {
        const h = m.w * 0.045;
        el("rect", { class: "part", x: s.x - s.w / 2, y: s.y - h / 2, width: s.w, height: h, rx: h / 2, "stroke-width": sw / 2 }, g);
        const t = el("text", { x: s.x, y: s.y + h * 0.18, "text-anchor": "middle", class: "pill-t", "font-size": h * 0.55 }, g);
        t.textContent = (MODEL_NAMES[kind] || {})[id] || id.toUpperCase();
      } else {
        el("circle", { class: "halo", cx: s.x, cy: s.y, r: s.r + sw * 1.7, filter: `url(#${fid})`, "stroke-width": sw * 3.7 }, g);
        el("circle", { class: "part ring", cx: s.x, cy: s.y, r: s.r, "stroke-width": sw }, g);
      }
    }
    return svg;
  }
  let MODEL_NAMES = {};

  function setOn(root, id, on) {
    const base = id.replace("_click", "");
    $$(`.ctl[data-id="${base}"]`, root).forEach((g) => g.classList.toggle("on", on));
  }

  async function main() {
    let data;
    try { data = await (await fetch("data/layout.json")).json(); } catch { return; }
    $$("[data-version]").forEach((n) => (n.textContent = data.version));
    MODEL_NAMES = data.names;

    // hero: cycle through buttons
    const hero = $('[data-pad="hero"]');
    if (hero) {
      hero.appendChild(padSvg("xbox", false));
      const keyEl = $("[data-ticker-key]"), actEl = $("[data-ticker-act]");
      let i = 0, prev = null;
      const tick = () => {
        const id = TICKER[i++ % TICKER.length];
        if (prev) setOn(hero, prev, false);
        setOn(hero, id, true); prev = id;
        keyEl.textContent = label("xbox", id);
        actEl.textContent = data.controls[id] || "";
      };
      tick();
      if (!reduced) setInterval(tick, 1900);
    }

    // button map
    const map = $('[data-pad="map"]');
    let kind = "xbox";
    function label(k, id) {
      const base = id.replace("_click", "");
      const n = data.names[k][base] || base.toUpperCase();
      if (id === "ls_click") return k === "playstation" ? "L3" : "LS click";
      if (id === "rs_click") return k === "playstation" ? "R3" : "RS click";
      if (id === "ls" && k === "playstation") return "Left stick";
      return n;
    }
    function renderBinds() {
      for (const [side, order] of [["left", ORDER_LEFT], ["right", ORDER_RIGHT]]) {
        const ul = $(`[data-binds="${side}"]`);
        ul.replaceChildren();
        for (const id of order) {
          if (!data.controls[id]) continue;
          const li = document.createElement("li");
          li.dataset.id = id;
          li.innerHTML = `<span class="key"></span><span class="act"></span>`;
          li.firstChild.textContent = label(kind, id);
          li.lastChild.textContent = data.controls[id];
          li.addEventListener("mouseenter", () => setOn(map, id, true));
          li.addEventListener("mouseleave", () => setOn(map, id, false));
          ul.appendChild(li);
        }
      }
    }
    function mountMap() {
      map.replaceChildren(padSvg(kind, true));
      $$(".ctl", map).forEach((g) => {
        const id = g.dataset.id;
        const on = (v) => {
          setOn(map, id, v);
          $$(`.binds li[data-id="${id}"], .binds li[data-id="${id}_click"]`).forEach((li) => li.classList.toggle("on", v));
        };
        g.addEventListener("mouseenter", () => on(true));
        g.addEventListener("mouseleave", () => on(false));
      });
    }
    if (map) {
      mountMap();
      renderBinds();
      $$("[data-pad-kind]").forEach((b) => b.addEventListener("click", () => {
        kind = b.dataset.padKind;
        $$("[data-pad-kind]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
        renderBinds();
        mountMap();
      }));
    }

    // demo: light the pad in step with the recording
    const vid = $("[data-demo]"), dpad = $('[data-pad="demo"]');
    if (vid && dpad) {
      dpad.appendChild(padSvg("xbox", false));
      let track = [];
      try { track = (await (await fetch("data/demo.json")).json()).events; } catch {}
      const keyEl = $("[data-demo-key]"), actEl = $("[data-demo-act]"), now = $(".demo-now");
      let cur = null;
      const sync = () => {
        const t = vid.currentTime;
        const e = track.filter((x) => x.t <= t + 0.05 && t - x.t < 1.1).at(-1);
        const id = e ? e.id : null;
        if (id === cur) return;
        if (cur) setOn(dpad, cur, false);
        cur = id; now.classList.toggle("on", !!id);
        if (id) { setOn(dpad, id, true); keyEl.textContent = label("xbox", id); actEl.textContent = id === "ls" ? "Walk" : data.controls[id]; }
      };
      vid.addEventListener("timeupdate", sync);
      (function loop() { if (!vid.paused) sync(); requestAnimationFrame(loop); })();
      if (reduced) { vid.removeAttribute("autoplay"); vid.pause(); vid.controls = true; }
    }

    // wheel
    const wheel = $("[data-wheel]");
    if (wheel) {
      drawWheel(wheel, data.wheel);
      const slices = $$(".slice", wheel), k = $("[data-wheel-key]"), a = $("[data-wheel-act]");
      let i = 0;
      const step = () => {
        slices.forEach((g, j) => g.classList.toggle("on", j === i));
        k.textContent = data.wheel[i].key; a.textContent = data.wheel[i].label.replace("Pokedex", "Pokédex");
        i = (i + 1) % slices.length;
      };
      step();
      if (!reduced) setInterval(step, 1600);
    }
  }

  function drawWheel(svg, slices) {
    const n = slices.length, R = 190, r0 = 62, step = (2 * Math.PI) / n;
    const pt = (a, rad) => [Math.sin(a) * rad, -Math.cos(a) * rad];
    slices.forEach((s, i) => {
      const a0 = i * step - step / 2, a1 = a0 + step;
      const [x0, y0] = pt(a0, R), [x1, y1] = pt(a1, R), [x2, y2] = pt(a1, r0), [x3, y3] = pt(a0, r0);
      const g = el("g", { class: "slice" + (i === 0 ? " top" : "") }, svg);
      el("path", { d: `M${x0} ${y0}A${R} ${R} 0 0 1 ${x1} ${y1}L${x2} ${y2}A${r0} ${r0} 0 0 0 ${x3} ${y3}Z` }, g);
      const [tx, ty] = pt(i * step, (R + r0) / 2);
      const words = s.label.split(" ");
      const lines = s.label.length > 12 && words.length > 1 ? [words.slice(0, -1).join(" "), words.at(-1)] : [s.label];
      lines.forEach((ln, j) => {
        const t = el("text", { x: tx, y: ty - 6 + (j - (lines.length - 1) / 2) * 15, "text-anchor": "middle" }, g);
        t.textContent = ln.replace("Pokedex", "Pokédex");
      });
      const k = el("text", { x: tx, y: ty + 12 + (lines.length - 1) * 7, "text-anchor": "middle", class: "k" }, g);
      k.textContent = s.key;
    });
    el("circle", { class: "hub", r: r0 - 8 }, svg);
    const t = el("text", { class: "hub-t", "text-anchor": "middle", y: 4 }, svg);
    t.textContent = "let go = cancel";
  }

  // install tabs: preselect the visitor's system
  function os() {
    const p = (navigator.userAgentData?.platform || navigator.platform || navigator.userAgent).toLowerCase();
    if (p.includes("win")) return "win";
    if (p.includes("mac")) return "mac";
    if (p.includes("linux") || p.includes("x11")) return "linux";
    return "win";
  }
  function pickOs(id) {
    $$("[data-os-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.osTab === id)));
    $$("[data-os-panel]").forEach((p) => (p.hidden = p.dataset.osPanel !== id));
  }
  $$("[data-os-tab]").forEach((b) => b.addEventListener("click", () => pickOs(b.dataset.osTab)));
  const mine = os();
  pickOs(mine);
  const osName = { win: "Windows", mac: "macOS", linux: "Linux & Deck" }[mine];
  $$("[data-os]").forEach((n) => (n.textContent = osName));

  $$("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    const code = b.closest(".term").querySelector("code").textContent;
    try { await navigator.clipboard.writeText(code); } catch { return; }
    b.textContent = "Copied"; b.classList.add("done");
    setTimeout(() => { b.textContent = "Copy"; b.classList.remove("done"); }, 1800);
  }));

  // nav border on scroll, reveal on scroll
  const nav = $(".nav");
  addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 8), { passive: true });

  // live star count (cached for an hour; the page works without it)
  (async () => {
    const out = $("[data-stars]");
    if (!out) return;
    let n;
    try {
      const c = JSON.parse(localStorage.getItem("pmc-stars") || "null");
      if (c && Date.now() - c.t < 3600e3) n = c.n;
    } catch {}
    if (n == null) {
      try {
        const r = await fetch("https://api.github.com/repos/jordanallenlewis/pokemmo-controller");
        n = (await r.json()).stargazers_count;
        try { localStorage.setItem("pmc-stars", JSON.stringify({ n, t: Date.now() })); } catch {}
      } catch { return; }
    }
    if (typeof n === "number") { out.textContent = n.toLocaleString(); out.hidden = false; }
  })();

  main();
})();
