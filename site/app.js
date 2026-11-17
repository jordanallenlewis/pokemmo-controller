// PokeMMO Controller site. No dependencies. Layout data comes from data/layout.json,
// which site/build.py writes from tools/layout.py (the same layout the installer puts on).
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Hotspots on the controller photo (assets/controller.webp, 1800 x 1303).
  // Shoulder buttons sit on the top edge, so they get pills above the photo.
  const SPOTS = {
    ls: { x: 435, y: 345, r: 120 }, rs: { x: 1257, y: 630, r: 112 },
    view: { x: 810, y: 348, r: 46 }, menu: { x: 1100, y: 348, r: 46 },
    y: { x: 1437, y: 228, r: 58 }, x: { x: 1323, y: 353, r: 58 },
    b: { x: 1565, y: 365, r: 58 }, a: { x: 1463, y: 480, r: 58 },
    dup: { x: 698, y: 598, r: 46 }, ddown: { x: 698, y: 770, r: 46 },
    dleft: { x: 606, y: 683, r: 46 }, dright: { x: 792, y: 683, r: 46 },
    lb: { pill: true, x: 430, y: -40, w: 210 }, rb: { pill: true, x: 1370, y: -40, w: 210 },
    lt: { pill: true, x: 430, y: -150, w: 210 }, rt: { pill: true, x: 1370, y: -150, w: 210 },
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

  function padSvg(interactive) {
    const svg = el("svg", { viewBox: "0 -230 1800 1533", role: "img", "aria-label": "Xbox controller" });
    const defs = el("defs", {}, svg);
    const f = el("filter", { id: interactive ? "gl-m" : "gl-h", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs);
    el("feGaussianBlur", { stdDeviation: "10" }, f);
    el("image", { href: "assets/controller.webp", x: 0, y: 0, width: 1800, height: 1303 }, svg);
    for (const [id, s] of Object.entries(SPOTS)) {
      const g = el("g", { class: "ctl" + (s.pill ? " pill" : ""), "data-id": id }, svg);
      if (s.pill) {
        el("rect", { class: "part", x: s.x - s.w / 2, y: s.y - 40, width: s.w, height: 80, rx: 40 }, g);
        const t = el("text", { x: s.x, y: s.y + 14, "text-anchor": "middle", class: "pill-t" }, g);
        t.textContent = id.toUpperCase();
      } else {
        el("circle", { class: "halo", cx: s.x, cy: s.y, r: s.r + 10, filter: `url(#${interactive ? "gl-m" : "gl-h"})` }, g);
        el("circle", { class: "part ring", cx: s.x, cy: s.y, r: s.r }, g);
      }
    }
    return svg;
  }

  function setOn(root, id, on) {
    const base = id.replace("_click", "");
    $$(`.ctl[data-id="${base}"]`, root).forEach((g) => g.classList.toggle("on", on));
  }

  async function main() {
    let data;
    try { data = await (await fetch("data/layout.json")).json(); } catch { return; }
    $$("[data-version]").forEach((n) => (n.textContent = data.version));

    // hero: cycle through buttons
    const hero = $('[data-pad="hero"]');
    if (hero) {
      hero.appendChild(padSvg(false));
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
    if (map) {
      map.appendChild(padSvg(true));
      renderBinds();
      $$(".ctl", map).forEach((g) => {
        const id = g.dataset.id;
        const on = (v) => {
          setOn(map, id, v);
          $$(`.binds li[data-id="${id}"], .binds li[data-id="${id}_click"]`).forEach((li) => li.classList.toggle("on", v));
        };
        g.addEventListener("mouseenter", () => on(true));
        g.addEventListener("mouseleave", () => on(false));
      });
      $$("[data-pad-kind]").forEach((b) => b.addEventListener("click", () => {
        kind = b.dataset.padKind;
        $$("[data-pad-kind]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
        renderBinds();
      }));
    }

    // wheel
    const wheel = $("[data-wheel]");
    if (wheel) drawWheel(wheel, data.wheel);
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
  if ("IntersectionObserver" in window && !reduced) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -10% 0px" });
    $$(".sec-head, .card, .map, .wheel-fig, .term, .shot, .faq").forEach((n) => { n.classList.add("reveal"); io.observe(n); });
  }

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
