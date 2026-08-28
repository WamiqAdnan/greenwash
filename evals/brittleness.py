#!/usr/bin/env python
"""How many of the Auditor's Closing Tests fire on output that is *correct*?

Kill Rate cannot tell "caught the bug" from "pinned the output". A test that
asserts the model's exact prose kills every Mutant, passes the Verification Gate
honestly, and would go red the next time someone rewords a prompt. By Kill Rate
it is a perfect test. To the engineer who owns the feature it is a pager at 3am
for nothing, and after two of those they stop believing the tool.

So this probe asks the opposite question to `run_eval.py`:

    run_eval      apply a sabotage. The suite SHOULD go red. Green is a Blind Spot.
    brittleness   apply a Benign Change. The suite SHOULD stay green. Red is a
                  False Alarm.

A Benign Change is a change a team really makes that does not break anything —
today, rewording the prompt. The Corpus Case declares the reworded prompt itself
and a human has read both, because "means the same thing" is not something to
leave to a regex.

    .venv/bin/python evals/brittleness.py
    .venv/bin/python evals/brittleness.py --case 03_rag_citations -v

Two guards, because a number here is only worth having if it is honest:

  If the Benign Change turns out to change nothing the Feature returns, there is
  no variation to probe and the case is reported as **not measured** rather than
  as a clean bill of health.

  If the case's *own* suite goes red under the Benign Change, then either the
  change was not benign or that suite is brittle too. Either way the Closing
  Tests are not what is being measured, and it is reported instead of scored.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auditor.agent import CLOSING_TEST_FILE, DEFAULT_SCRATCH  # noqa: E402
from greenwash import harness, observe, operators as ops  # noqa: E402

CLOSING = ROOT / "auditor" / "closing_tests"
FAILED = re.compile(r"^FAILED \S+::(\w+)", re.M)


def closing_test_names(code: str) -> list[str]:
    return re.findall(r"def (test_\w+)", code)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", type=Path, default=ROOT / "evals" / "brittleness.json")
    args = ap.parse_args()

    cases = harness.discover()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            raise SystemExit(f"no such case: {args.case}")

    rows, total_tests, total_alarms = [], 0, 0
    for case in cases:
        print(f"\n{case.name}")
        path = CLOSING / f"{case.name}.py"
        code = path.read_text() if path.exists() else ""
        names = closing_test_names(code)
        if not names:
            print("  no closing tests — nothing to probe")
            continue

        merged = harness.overlay(
            case, {CLOSING_TEST_FILE: code}, DEFAULT_SCRATCH / case.name / "brittle"
        )
        clean = observe.observe(case.path)

        for change in ops.applicable_benign(case.tags):
            changed = observe.observe(case.path, change.id)
            if observe.failed(changed) or changed == clean:
                print(f"  {change.id}: the feature returned exactly the same thing — "
                      f"no variation to probe, not measured")
                rows.append({"case": case.name, "change": change.id,
                             "measured": False, "why": "the change was inert"})
                continue

            suite_green, suite_out = case.run_suite(change.id)
            if not suite_green:
                print(f"  ! {change.id}: the case's OWN suite goes red under this. "
                      f"Either the change is not benign or that suite is brittle "
                      f"too — not scored.")
                if args.verbose:
                    print(f"    {harness._first_failure(suite_out)}")
                rows.append({"case": case.name, "change": change.id,
                             "measured": False, "why": "the original suite went red"})
                continue

            green, out = merged.run_suite(change.id, select=f"tests/{CLOSING_TEST_FILE}")
            alarms = sorted(set(FAILED.findall(out)))
            total_tests += len(names)
            total_alarms += len(alarms)
            print(f"  {change.id}: {change.summary}")
            print(f"    the feature still returns a correct answer, worded differently")
            print(f"    the case's own suite: green")
            print(f"    closing tests: {len(alarms)} of {len(names)} raised a "
                  f"FALSE ALARM")
            for name in alarms:
                print(f"      - {name}")
            rows.append({"case": case.name, "change": change.id, "measured": True,
                         "closing_tests": len(names), "false_alarms": alarms})

    print(f"\n{'=' * 52}")
    if total_tests:
        print(f"false alarm rate  {total_alarms}/{total_tests} "
              f"({total_alarms / total_tests:.0%}) of closing tests go red on "
              f"output that is correct")
    else:
        print("nothing measurable — no benign change moved any feature's output")
    args.json.write_text(json.dumps({"cases": rows}, indent=2))
    print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
