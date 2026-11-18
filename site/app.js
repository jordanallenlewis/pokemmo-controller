// PokeMMO Controller site. No dependencies. Layout data comes from data/layout.json,
// which site/build.py writes from tools/layout.py (the same layout the installer puts on).
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Photos, hotspots, button names and what each button does all come from data/layout.json,
  // which site/build.py writes from tools/layout.py and data/hotspots.json. Nothing is restated here.
  let PADS = {};
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
    const m = PADS[kind], top = m.w * 0.06 * 2.4 + m.w * 0.04, sw = m.w / 300;
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
        t.textContent = m.names[id] || id.toUpperCase();
      } else {
        el("circle", { class: "halo", cx: s.x, cy: s.y, r: s.r + sw * 1.7, filter: `url(#${fid})`, "stroke-width": sw * 3.7 }, g);
        el("circle", { class: "part ring", cx: s.x, cy: s.y, r: s.r, "stroke-width": sw }, g);
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
    PADS = data.pads;

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
        actEl.textContent = PADS.xbox.controls[id] || "";
      };
      tick();
      if (!reduced) setInterval(tick, 1900);
    }

    // button map
    const map = $('[data-pad="map"]');
    let kind = "xbox";
    function label(k, id) { return data.pads[k].names[id] || id.toUpperCase(); }
    function renderBinds() {
      for (const [side, order] of [["left", ORDER_LEFT], ["right", ORDER_RIGHT]]) {
        const ul = $(`[data-binds="${side}"]`);
        ul.replaceChildren();
        for (const id of order) {
          if (!data.pads[kind].controls[id]) continue;
          const li = document.createElement("li");
          li.dataset.id = id;
          li.innerHTML = `<span class="key"></span><span class="act"></span>`;
          li.firstChild.textContent = label(kind, id);
          li.lastChild.textContent = data.pads[kind].controls[id];
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
        if (id) { setOn(dpad, id, true); keyEl.textContent = label("xbox", id); actEl.textContent = e.label || data.controls[id]; }
      };
      vid.addEventListener("timeupdate", sync);
      (function loop() { if (!vid.paused) sync(); requestAnimationFrame(loop); })();
      // the poster is fetched when the demo is near, not with the first paint
      const poster = () => { if (!vid.poster) vid.poster = vid.dataset.poster; };
      if ("IntersectionObserver" in window) {
        const near = new IntersectionObserver((es) => { if (es.some((en) => en.isIntersecting)) { poster(); near.disconnect(); } }, { rootMargin: "600px" });
        near.observe(vid);
      } else poster();
      // fetch and play the recording only once it is on screen, so it does not compete with the first paint
      if (reduced) vid.controls = true;
      else if ("IntersectionObserver" in window) {
        new IntersectionObserver((es) => es.forEach((en) => {
          if (en.isIntersecting) { vid.preload = "auto"; vid.play().catch(() => { vid.controls = true; }); } else vid.pause();
        }), { threshold: 0.25 }).observe(vid);
      } else vid.controls = true;
    }

    // wheel
    const wheel = $("[data-wheel]");
    if (wheel) {
      drawWheel(wheel, data.wheel);
      const slices = $$(".slice", wheel), k = $("[data-wheel-key]"), a = $("[data-wheel-act]");
      let i = 0;
      const step = () => {
        slices.forEach((g, j) => g.classList.toggle("on", j - 1 === i));
        k.textContent = data.wheel[i].key; a.textContent = data.wheel[i].label.replace("Pokedex", "Pokédex");
        i = (i + 1) % slices.length;
      };
      step();
      if (!reduced) setInterval(step, 1600);
    }
  }

  function drawWheel(svg, slices) {
    slices = [{ key: "", label: "Nothing" }, ...slices];   // the top slice does nothing, so a stray flick up presses nothing
    const n = slices.length, R = 190, r0 = 62, step = (2 * Math.PI) / n;
    const pt = (a, rad) => [Math.sin(a) * rad, -Math.cos(a) * rad];
    slices.forEach((s, i) => {
      const a0 = i * step - step / 2, a1 = a0 + step;
      const [x0, y0] = pt(a0, R), [x1, y1] = pt(a1, R), [x2, y2] = pt(a1, r0), [x3, y3] = pt(a0, r0);
      const g = el("g", { class: "slice" + (i === 0 ? " top" : "") }, svg);
      el("path", { d: `M${x0} ${y0}A${R} ${R} 0 0 1 ${x1} ${y1}L${x2} ${y2}A${r0} ${r0} 0 0 0 ${x3} ${y3}Z` }, g);
      const [tx, ty] = pt(i * step, (R + r0) / 2);
      const words = s.label.split(" ");
      let lines = [s.label];
      if (s.label.length > 9 && words.length > 1) {          // two short lines fit a slice better than one long one
        let best = 1;
        for (let j = 1; j < words.length; j++)
          if (Math.abs(words.slice(0, j).join(" ").length - words.slice(j).join(" ").length) < Math.abs(words.slice(0, best).join(" ").length - words.slice(best).join(" ").length)) best = j;
        lines = [words.slice(0, best).join(" "), words.slice(best).join(" ")];
      }
      lines.forEach((ln, j) => {
        const t = el("text", { x: tx, y: ty - 6 + (j - (lines.length - 1) / 2) * 15, "text-anchor": "middle" }, g);
        t.textContent = ln.replace("Pokedex", "Pokédex");
      });
      if (s.key) {
        const k = el("text", { x: tx, y: ty + 12 + (lines.length - 1) * 7, "text-anchor": "middle", class: "k" }, g);
        k.textContent = s.key;
      }
    });
    el("circle", { class: "hub", r: r0 - 8 }, svg);
    const t = el("text", { class: "hub-t", "text-anchor": "middle", y: 4 }, svg);
    t.textContent = "let go = cancel";
  }

  // install tabs: preselect the visitor's real system. Phones and tablets cannot run the
  // installer, so say so instead of guessing a desktop system for them.
  function detect() {
    const ua = navigator.userAgent || "";
    const p = (navigator.userAgentData?.platform || navigator.platform || "").toLowerCase();
    if (/android|iphone|ipad|ipod/i.test(ua) || (p.includes("mac") && navigator.maxTouchPoints > 1)) return "mobile";
    if (/steamdeck|steamos/i.test(ua)) return "deck";
    if (p.includes("win") || /windows/i.test(ua)) return "win";
    if (p.includes("mac")) return "mac";
    if (p.includes("linux") || p.includes("x11") || /linux|x11|cros/i.test(ua)) return "linux";
    return null;
  }
  function pickOs(id) {
    $$("[data-os-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.osTab === id)));
    $$("[data-os-panel]").forEach((p) => (p.hidden = p.dataset.osPanel !== id));
    $$("[data-undo-panel]").forEach((p) => (p.hidden = p.dataset.undoPanel !== (id === "win" ? "win" : "unix")));
  }
  $$("[data-os-tab]").forEach((b) => b.addEventListener("click", () => pickOs(b.dataset.osTab)));
  const NAMES = { win: "Windows", mac: "macOS", linux: "Linux", deck: "Steam Deck" };
  const mine = detect();
  pickOs(NAMES[mine] ? mine : "win");
  if (NAMES[mine]) {
    $$("[data-os]").forEach((n) => (n.textContent = NAMES[mine]));
  } else if (mine === "mobile") {
    const note = $("[data-os-note]");
    if (note) { note.hidden = false; note.textContent = "This installs on the computer or Steam Deck you play PokeMMO on. "; }
  }

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
