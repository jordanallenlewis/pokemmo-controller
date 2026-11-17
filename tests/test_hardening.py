"""Extra guards: the exact bind text PokeMMO reads (golden file), a seeded fuzz of the
one-input-one-action rules, random layouts through install and uninstall, and static
checks of the remap page. Standard library only, no browser, same on every OS."""
import json, random, re, unittest
from html.parser import HTMLParser
from pathlib import Path

import helpers  # noqa: F401
import layout as L
import apply_native
from test_setup import Base, diff

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "binds-default.txt"


def random_valid(rng):
    """A layout that obeys every rule: each action on its own input, wheel shuffled."""
    inputs = L.inputs()
    rng.shuffle(inputs)
    lay = {"format": L.FORMAT, "binds": dict(zip(L.ACTIONS, inputs)), "wheel": list(L.WHEEL_ACTIONS)}
    rng.shuffle(lay["wheel"])
    return lay


class GoldenBinds(unittest.TestCase):
    def test_default_binds_text_is_exact(self):
        want = GOLDEN.read_bytes().replace(b"\r\n", b"\n").decode("utf-8").splitlines()
        binds = L.native_binds(L.default_layout())
        got = [apply_native.encode_one(name, True, binds) for name in
               ("Xbox Series X Controller", "Xbox One S Controller", "PS5 Controller",
                "Pro Controller", "Nintendo Switch Pro Controller")]
        self.assertEqual(got, want)

    def test_shipped_default_equals_default_layout_file(self):
        # the no-layout path and the layout path write the same bytes for Xbox pads
        self.assertEqual(apply_native.encode_one("Xbox Series X Controller"),
                         apply_native.encode_one("Xbox Series X Controller", True, L.native_binds(L.default_layout())))


class Fuzz(unittest.TestCase):
    def test_random_valid_layouts_are_accepted_and_one_to_one(self):
        rng = random.Random(1103)
        for _ in range(200):
            lay = random_valid(rng)
            L.validate(lay)
            inputs = list(L.native_binds(lay).values())
            self.assertEqual(len(inputs), len(set(inputs)))
            self.assertEqual(L.loads(L.dumps(lay)), lay)

    def test_no_pad_name_gets_two_actions_on_one_input(self):
        # Nintendo pads swap face buttons to follow the printed letters: that swap must
        # move buttons, not actions, or a custom layout lands two actions on one button.
        rng = random.Random(4242)
        for _ in range(200):
            binds = L.native_binds(random_valid(rng))
            for name in apply_native.CONTROLLER_NAMES:
                for labels in (True, False):
                    parts = apply_native.encode_one(name, labels, binds).split(";")[1:]
                    inputs = [x.split(",", 1)[1] for x in parts]
                    self.assertEqual(len(inputs), len(set(inputs)), (name, labels, parts))

    def test_every_mutation_is_refused_or_stays_one_to_one(self):
        rng = random.Random(2077)
        junk = [None, True, -1, 15, 99, 1.5, "1", [], [1, 2], {}, {"button": 1}, "KEY_A", 10**30]
        refused = 0
        for _ in range(600):
            lay = random_valid(rng)
            kind = rng.randrange(5)
            a = rng.choice(list(L.ACTIONS))
            if kind == 0:
                lay["binds"][a] = rng.choice(junk)
            elif kind == 1:
                lay["binds"][a] = {rng.choice(["button", "axis"]): rng.choice(junk), "positive": rng.choice(junk)}
            elif kind == 2:
                lay["binds"][a] = {"button": 0, rng.choice(["repeat", "turbo", "hold", "delay", "then", "macro"]): rng.choice(junk)}
            elif kind == 3:
                lay["wheel"][rng.randrange(len(lay["wheel"]))] = rng.choice(junk + list(L.WHEEL_ACTIONS))
            else:
                lay[rng.choice(["macro", "repeat", "turbo", "sequence", "delay"])] = rng.choice(junk)
            try:
                L.validate(lay)
            except L.LayoutError:
                refused += 1
                continue
            except Exception as e:  # a crash is a bug: refusal must be a LayoutError
                self.fail(f"validate crashed on {lay!r}: {e!r}")
            inputs = list(L.native_binds(lay).values())
            self.assertEqual(len(inputs), len(set(inputs)), lay)
            self.assertFalse([i for i in inputs if i[0] == "AXIS" and i[1] in L.TRIGGERS and not i[2]], lay)
            self.assertEqual(len(set(lay["wheel"])), len(lay["wheel"]))
        self.assertGreater(refused, 300)

    def test_garbage_text_never_crashes_the_reader(self):
        rng = random.Random(7)
        base = L.dumps(L.default_layout())
        for _ in range(300):
            s = list(base)
            for _ in range(rng.randrange(1, 6)):
                s[rng.randrange(len(s))] = rng.choice('{}[]",:0 x\n\u0000é')
            try:
                L.loads("".join(s))
            except L.LayoutError:
                pass


class RandomLayoutsRoundTrip(Base):
    def test_install_and_uninstall_are_exact_for_random_layouts(self):
        rng = random.Random(42)
        for i in range(3):
            sb = self.make()
            before = sb.snapshot()
            f = sb.root / "mine.json"
            f.write_text(json.dumps(random_valid(rng)), encoding="utf-8")
            sb.setup("--layout", str(f))
            installed = sb.snapshot()
            self.assertEqual(diff(installed, sb.setup("--layout", str(f)) and sb.snapshot()), [])
            sb.setup("--uninstall")
            after = {k: v for k, v in sb.snapshot().items() if not k.endswith("mine.json")}
            self.assertEqual(diff(before, after), [], f"round {i}")


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs, self.urls, self.inputs, self.labels, self.scripts = set(), [], [], [], set(), []
        self._script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("src", "href", "action"):
            if k in a:
                self.urls.append((tag, a[k]))
        if tag == "script":
            self._script = True
            if "src" in a:
                self.scripts.append("external")
        if tag in ("input", "select", "textarea") and a.get("type") != "hidden":
            self.inputs.append(a)
        if tag == "label" and "for" in a:
            self.labels.add(a["for"])

    def handle_endtag(self, tag):
        if tag == "script":
            self._script = False

    def handle_data(self, data):
        if self._script:
            self.scripts.append(data)


class Page(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "tools" / "ui_page.html").read_text(encoding="utf-8")
        self.scan = _Scan()
        self.scan.feed(self.text)
        self.js = "\n".join(s for s in self.scan.scripts)

    def test_no_external_files_and_no_network_calls_to_other_hosts(self):
        self.assertNotIn("external", self.scan.scripts)
        for tag, url in self.scan.urls:
            self.assertFalse(re.match(r"(?i)(https?:)?//", url), (tag, url))
        for m in re.finditer(r"""(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(\s*["'`]?([^"'`),]*)""", self.js):
            self.assertFalse(re.match(r"(?i)(https?|wss?):", m.group(1)), m.group(0))
        self.assertNotRegex(self.js, r"\bimport\s*\(|importScripts|navigator\.sendBeacon")

    def test_every_id_the_script_asks_for_exists(self):
        for m in re.finditer(r"""\$\(\s*["']([\w-]+)["']\s*\)""", self.js):
            self.assertIn(m.group(1), self.scan.ids, m.group(0))
        for m in re.finditer(r"""getElementById\(\s*["']([\w-]+)["']""", self.js):
            self.assertIn(m.group(1), self.scan.ids, m.group(0))

    def test_page_basics_for_screen_readers_and_zoom(self):
        self.assertRegex(self.text, r"<html[^>]*\blang=")
        self.assertRegex(self.text, r'<meta[^>]+name="viewport"')
        self.assertRegex(self.text, r"<title>[^<]+</title>")
        self.assertEqual(len(re.findall(r"<h1\b", self.text)), 1)
        # sizes scale with the player's text setting; the wheel's labels are SVG units, which scale with the picture
        for line in self.text.splitlines():
            if not line.lstrip().startswith("#wheel"):
                self.assertNotRegex(line, r"font-size:\s*\d+px")

    def test_pad_picker_and_button_map_are_labelled(self):
        self.assertIn("pad", self.scan.ids)
        self.assertRegex(self.text, r'<label[^>]+for="pad"')
        self.assertIn("map", self.scan.ids)
        self.assertRegex(self.text, r'<svg[^>]+id="map"[^>]+role="group"[^>]+aria-label="[^"]+"')

    def test_page_has_no_macro_controls(self):
        low = self.text.lower()
        for word in ("turbo", "auto-repeat", "autorepeat", "macro", "sequence", "delay", "rapid"):
            if word in low:
                # only allowed inside a sentence that says the tool does NOT do it
                for m in re.finditer(word, low):
                    around = low[max(0, m.start() - 80): m.end() + 80]
                    self.assertRegex(around, r"\b(no|not|never|refus|without)", (word, around))


if __name__ == "__main__":
    unittest.main()
