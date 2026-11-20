"""The remap page's checklist buttons, run for real: the page script executes in a stubbed DOM
(node) against a live ui.py server on a sandbox. A button that is enabled must do something.

Needs node. CI has it; a missing node is a failure here, never a skip."""
import json, shutil, subprocess, unittest
from pathlib import Path

import helpers  # noqa: F401  (tools/ on the path, test mode on)
import test_ui
from test_setup import Base

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / "tools" / "ui_page.html"


class PageBehavior(Base):
    start = test_ui.UI.start
    call = test_ui.UI.call

    def test_fix_button_works_when_pokemmo_turns_up_after_load(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for this test (preinstalled on the CI runners)")
        sb = self.make()
        gone = sb.pokemmo.with_name("Poke MMO away")
        self.start(sb)
        base = f"http://127.0.0.1:{self.port}"
        p = subprocess.run([node, str(HERE / "ui_page_harness.js"), str(PAGE), base, self.app.token, str(sb.pokemmo), str(gone)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout.strip().splitlines()[-1])
        print("harness:", out)
        if out["enabled"]:
            self.assertIn("POST /api/apply", out["sent"], "an enabled button did nothing")
        else:
            self.assertTrue(False, "no enabled fix button after PokeMMO turned up: " + str(out))

    def test_late_pokemmo_never_writes_the_default_over_a_saved_custom_layout(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for this test (preinstalled on the CI runners)")
        sb = self.make()
        gone = sb.pokemmo.with_name("Poke MMO away")
        self.start(sb)
        base = f"http://127.0.0.1:{self.port}"
        lay = test_ui.L.default_layout()
        lay["binds"]["KEY_INVENTORY"], lay["binds"]["KEY_RING_FOCUS"] = ({"button": 9}, {"button": 10})
        self.assertTrue(self.call("POST", "/api/apply", {"layout": lay})[1]["ok"])
        self.assertTrue(self.call("GET", "/api/state")[1]["custom"])
        p = subprocess.run([node, str(HERE / "ui_page_harness.js"), str(PAGE), base, self.app.token, str(sb.pokemmo), str(gone), "main"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout.strip().splitlines()[-1])
        print("harness:", out)
        # Apply may stay off, but if it goes out it must carry the saved layout, never the default
        for sent in out["applied"]:
            self.assertEqual(sent, lay, "Apply wrote a layout that is not the saved one")
        self.assertEqual(self.call("GET", "/api/state")[1]["layout"], lay)
        self.assertTrue(self.call("GET", "/api/state")[1]["custom"])
        self.assertTrue(out["enabled"], "Apply should be on once the saved layout is loaded: " + str(out))
        self.assertEqual(len(out["applied"]), 1, out)


if __name__ == "__main__":
    unittest.main()
