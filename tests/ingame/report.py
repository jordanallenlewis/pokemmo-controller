"""Turn an in-game run's results into the pass/fail table for a PR.

    python tests/ingame/report.py results.json > table.md

results.json: {"branch": "...", "commit": "...", "results": {"B3": {"status": "pass",
"screenshot": "shots/B3.png", "note": ""}, ...}}. A step with no result counts as a
fail, so a run that stops early cannot read as green. Exit code 1 on any failure.
Standard library only."""
import json, sys
from pathlib import Path

CHECKLIST = Path(__file__).with_name("checklist.json")


def steps(checklist):
    for phase in checklist["phases"]:
        for s in phase["steps"]:
            yield phase, s


def build(checklist, run):
    results = run.get("results", {})
    rows, failed = [], 0
    for phase, s in steps(checklist):
        r = results.get(s["id"])
        if r is None and s.get("optional"):
            status = "skipped"
        else:
            status = (r or {}).get("status", "fail") if r else "fail"
        if status == "fail":
            failed += 1
        shot = (r or {}).get("screenshot", "")
        what = s.get("action") or s.get("do", "")
        rows.append(f"| {s['id']} | {phase['name']} | {what} | {status.upper()} | {shot} |")
    head = [f"In-game run: {run.get('branch', '?')} @ {run.get('commit', '?')[:7]}", "",
            f"{'PASS' if not failed else 'FAIL'}: {failed} failing step(s)", "",
            "| Step | Phase | What | Result | Screenshot |", "|---|---|---|---|---|"]
    tail = ["", "Not covered by this run:"] + [f"- {x}" for x in checklist["not_covered_here"]]
    return "\n".join(head + rows + tail), failed


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    run = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    text, failed = build(checklist, run)
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
