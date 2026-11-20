"""The remap screen on an install a newer PokeMMO Controller made (record_format 2 and up).

This copy only reads such an install (docs/FOUNDATION.md M1). The screen says so up front with
the shared sentence from common.NEWER, and turns off every button that would write (Apply, the
checklist's fix buttons, back to defaults, load a file) instead of offering them and refusing
after the click. The pad test and the layout view keep working.
"""
import re, unittest
from pathlib import Path

import helpers  # noqa: F401  (tools/ on the path, test mode on)
import common
from test_newer_record import make_newer
from test_setup import Base, diff
import test_ui

PAGE = (Path(__file__).resolve().parent.parent / "tools" / "ui_page.html").read_text(encoding="utf-8")


def js_function(name):
    """The body of a top-level `function name(...) {...}` in the page script (brace matched)."""
    m = re.search(r"\n(?:async )?function " + re.escape(name) + r"\([^)]*\) \{", PAGE)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth and i < len(PAGE):
        depth += {"{": 1, "}": -1}.get(PAGE[i], 0)
        i += 1
    return PAGE[m.end():i - 1]


class NewerServer(Base):
    start = test_ui.UI.start
    call = test_ui.UI.call

    def newer_install(self):
        sb = self.make()
        sb.setup()
        make_newer(sb, record_format=2, version="2.0.0")
        self.start(sb)
        return sb

    def test_state_says_a_newer_version_made_the_install(self):
        self.newer_install()
        st = self.call("GET", "/api/state")[1]
        self.assertTrue(st["status"]["newer"])
        self.assertEqual(st["newer_text"], common.NEWER)
        self.assertTrue(self.call("GET", "/api/status")[1]["newer"])

    def test_own_install_is_not_newer(self):
        sb = self.make()
        sb.setup()
        self.start(sb)
        st = self.call("GET", "/api/state")[1]
        self.assertFalse(st["status"]["newer"])
        self.assertEqual(st["newer_text"], common.NEWER)   # always sent; the page shows it only when newer

    def test_writes_sent_anyway_change_nothing(self):
        sb = self.newer_install()
        before = sb.snapshot()
        for path, body in (("/api/apply", {"layout": test_ui.L.default_layout()}), ("/api/reset", {})):
            with self.subTest(path=path):
                r = self.call("POST", path, body)[1]
                self.assertFalse(r["ok"], r)
                self.assertIn(common.NEWER, r["output"])
        self.assertEqual(diff(before, sb.snapshot()), [], "a refused write changed files")


class NewerPage(unittest.TestCase):
    """No browser in CI: these read the page script. A headless check of the same page is in the PR."""

    def test_the_sentence_comes_from_the_program_not_a_copy(self):
        self.assertNotIn(common.NEWER, PAGE)
        self.assertIn("S.newer_text", PAGE)
        self.assertRegex(PAGE, r'<div id="newer" class="note warn" role="status"[^>]*hidden>')

    def test_the_gates(self):
        edit, write = js_function("canEdit"), js_function("canWrite")
        self.assertIsNotNone(edit, "the page has no canEdit()")
        self.assertIsNotNone(write, "the page has no canWrite()")
        self.assertRegex(edit, r"return !busy && !S\.status\.newer;")
        # Apply also needs PokeMMO's settings; editing a layout (defaults, a file) does not
        self.assertRegex(write, r"return canEdit\(\) && !S\.problem;")

    def test_every_write_button_follows_a_gate(self):
        bar = js_function("renderBar") or ""
        self.assertIn('$("apply").disabled = !canWrite();', bar)
        m = re.search(r"for \(const id of \[([^\]]*)\]\) \$\(id\)\.disabled = !canEdit\(\);", bar)
        self.assertIsNotNone(m, "renderBar does not set defaults/import from canEdit()")
        self.assertEqual(set(re.findall(r'"([\w-]+)"', m.group(1))), {"defaults", "import"})

    def test_checklist_offers_no_fix_button_on_a_newer_install(self):
        body = js_function("drawChecklist") or ""
        self.assertRegex(body, r"if \(!s\.ok && s\.fix && !st\.newer\)")
        self.assertIn("else if (!canEdit()) b.disabled = true;", body)

    def test_apply_stops_at_the_gate_and_holds_it_while_running(self):
        body = js_function("apply")
        self.assertRegex(body or "", r"^\s*if \(!canWrite\(\)\) return;")
        self.assertIn("busy = true", body)
        self.assertIn("busy = false", body)

    def test_reading_still_works(self):
        # Save layout file and the pad test do not write to the install: never gated
        bar = js_function("renderBar")
        self.assertNotIn('"export"', bar)
        self.assertNotIn("canWrite", js_function("pollPads"))


if __name__ == "__main__":
    unittest.main()
