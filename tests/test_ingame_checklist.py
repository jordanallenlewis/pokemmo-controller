"""The in-game checklist stays in step with the layout: every bound action has a step,
every step does one thing once, and the report cannot read green when steps are missing."""
import json, sys, unittest
from pathlib import Path

import helpers  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests" / "ingame"))
import apply_native  # noqa: E402
import report  # noqa: E402

CHECKLIST = json.loads((ROOT / "tests" / "ingame" / "checklist.json").read_text(encoding="utf-8"))
STEPS = [s for _, s in report.steps(CHECKLIST)]


class Checklist(unittest.TestCase):
    def test_every_bound_action_has_a_step(self):
        covered = {s["action"] for s in STEPS if "action" in s}
        self.assertEqual(set(apply_native.LAYOUT) - covered, set())

    def test_step_ids_are_unique(self):
        ids = [s["id"] for s in STEPS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_step_repeats_holds_or_chains(self):
        for s in STEPS:
            text = " ".join(str(v) for k, v in s.items() if k in ("do", "input")).lower()
            for bad in ("repeat", "hold ", "keep pressing", "mash", "loop", "every second", "then press"):
                self.assertNotIn(bad, text, f"{s['id']}: one input, one action ({bad!r})")

    def test_missing_results_are_failures(self):
        text, failed = report.build(CHECKLIST, {"branch": "x", "commit": "abc1234", "results": {}})
        self.assertGreater(failed, 0)
        self.assertIn("FAIL", text)

    def test_all_pass_is_green(self):
        results = {s["id"]: {"status": "pass"} for s in STEPS}
        _, failed = report.build(CHECKLIST, {"results": results})
        self.assertEqual(failed, 0)

    def test_no_secrets_or_account_names(self):
        raw = (ROOT / "tests" / "ingame" / "checklist.json").read_text(encoding="utf-8").lower()
        for bad in ("password", "windward"):
            self.assertNotIn(bad, raw)


if __name__ == "__main__":
    unittest.main()
