// Runs the remap page's own script in a stubbed DOM against a real ui.py server.
// usage: node ui_page_harness.js <page.html> <base-url> <key> <pokemmo-dir> <away-dir>
// Sequence: PokeMMO missing at load -> it turns up -> the 5 s status refresh fires -> click the
// first enabled checklist button. Prints one JSON line: requests sent and the visible result.
const fs = require("fs"), vm = require("vm");
const [page, base, key, dir, away] = process.argv.slice(2);
const html = fs.readFileSync(page, "utf8");
const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

function makeEl(tag) {
  const e = {tag, attrs: {}, kids: [], listeners: {}, disabled: false, hidden: false, title: "", value: "", checked: false,
    dataset: {}, style: {}, _text: ""};
  e.classList = {add() {}, remove() {}, toggle() {}, contains: () => false};
  e.setAttribute = (k, v) => { e.attrs[k] = v; };
  e.getAttribute = (k) => e.attrs[k];
  e.removeAttribute = (k) => { delete e.attrs[k]; };
  e.append = (...k) => { for (const x of k) e.kids.push(x); };
  e.appendChild = (k) => { e.kids.push(k); return k; };
  e.addEventListener = (n, f) => { (e.listeners[n] = e.listeners[n] || []).push(f); };
  e.focus = () => {}; e.click = () => {};
  e.getBoundingClientRect = () => ({left: 0, top: 0, width: 100, height: 100});
  Object.defineProperty(e, "textContent", {get: () => e._text + e.kids.map((k) => k.textContent || "").join(""),
    set: (v) => { e._text = v; e.kids = []; }});
  return new Proxy(e, {get: (t, p) => (p in t || typeof p === "symbol") ? t[p] : (() => makeEl("x"))});
}
const ids = {};
const body = makeEl("body"); body.dataset.key = key;
const document = {
  body, hidden: false,
  getElementById: (id) => ids[id] || (ids[id] = makeEl("div")),
  createElement: makeEl, createElementNS: (ns, t) => makeEl(t),
  querySelectorAll: () => [],
};
const requests = [];
const realFetch = global.fetch;
const fetch = (path, opts) => {
  requests.push((opts && opts.method || "GET") + " " + path);
  return realFetch(base + path, opts);
};
const timers = [];
const ctx = {document, fetch, setInterval: (f, ms) => { timers.push([f, ms]); return timers.length; }, setTimeout, console,
  history: {replaceState() {}}, navigator: {getGamepads: () => []}, localStorage: {getItem: () => null, setItem() {}}, location: {hash: ""}, window: {},
  URL, Blob, JSON, Object, Math, Date, Promise};
vm.createContext(ctx);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  fs.renameSync(dir, away);
  vm.runInContext(script, ctx);
  await sleep(1500);                       // init() finished: problem set at load
  fs.renameSync(away, dir);
  const status = timers.find(([, ms]) => ms === 5000)[0];
  status(); await sleep(1500);             // the 5 s refresh found PokeMMO
  const list = ids["checklist"];
  const btn = list.kids.map((li) => li.kids.find((k) => k.tag === "button" && !k.disabled)).find(Boolean);
  const enabled = !!btn;
  const before = requests.length;
  if (btn) { btn.listeners.click.forEach((f) => f()); await sleep(4000); }
  console.log(JSON.stringify({enabled, sent: requests.slice(before), result: ids["result"] ? ids["result"].textContent : ""}));
  process.exit(0);
})();
