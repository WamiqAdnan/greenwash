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

Read each row for which kind of Benign Change produced it. The Verification Gate
applies most of them itself before accepting a Closing Test, so those rows are
the Gate's own rule reported back — a regression check, worth having, but not a
second opinion. A row marked **held out** is one the Gate is not allowed to
touch: nothing upstream has already enforced it, so a False Alarm there is a
finding and a zero there is evidence. The summary counts them separately for
that reason.

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

    # Held out from the Gate and applied by it are counted apart, because they
    # are different claims and averaging them would hide the only one that is
    # independent evidence.
    rows = []
    tally = {True: [0, 0], False: [0, 0]}   # held_out -> [tests, alarms]
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
            held_out = change.id in ops.HELD_OUT
            changed = observe.observe(case.path, change.id)
            if observe.failed(changed) or changed == clean:
                print(f"  {change.id}: the feature returned exactly the same thing — "
                      f"no variation to probe, not measured")
                rows.append({"case": case.name, "change": change.id,
                             "held_out": held_out, "measured": False,
                             "why": "the change was inert"})
                continue

            suite_green, suite_out = case.run_suite(change.id)
            if not suite_green:
                print(f"  ! {change.id}: the case's OWN suite goes red under this. "
                      f"Either the change is not benign or that suite is brittle "
                      f"too — not scored.")
                if args.verbose:
                    print(f"    {harness._first_failure(suite_out)}")
                rows.append({"case": case.name, "change": change.id,
                             "held_out": held_out, "measured": False,
                             "why": "the original suite went red"})
                continue

            green, out = merged.run_suite(change.id, select=f"tests/{CLOSING_TEST_FILE}")
            alarms = sorted(set(FAILED.findall(out)))
            tally[held_out][0] += len(names)
            tally[held_out][1] += len(alarms)
            standing = (
                "HELD OUT of the gate — nothing upstream enforced this"
                if held_out else
                "the gate applies this too — a regression check, not a second opinion"
            )
            print(f"  {change.id}: {change.summary}")
            print(f"    {standing}")
            print(f"    the feature still returns a correct answer, worded differently")
            print(f"    the case's own suite: green")
            print(f"    closing tests: {len(alarms)} of {len(names)} raised a "
                  f"FALSE ALARM")
            for name in alarms:
                print(f"      - {name}")
            rows.append({"case": case.name, "change": change.id,
                         "held_out": held_out, "measured": True,
                         "closing_tests": len(names), "false_alarms": alarms})

    print(f"\n{'=' * 52}")
    held_tests, held_alarms = tally[True]
    gate_tests, gate_alarms = tally[False]
    if held_tests:
        print(f"false alarm rate  {held_alarms}/{held_tests} "
              f"({held_alarms / held_tests:.0%})  under HELD-OUT benign changes "
              f"— the gate never saw these, so this is the number that counts")
    else:
        print("no held-out benign change moved any feature's output — nothing "
              "here is independent of the gate")
    if gate_tests:
        print(f"                  {gate_alarms}/{gate_tests} "
              f"({gate_alarms / gate_tests:.0%})  under benign changes the gate "
              f"applies itself — a regression check on the gate")
    if not held_tests and not gate_tests:
        print("nothing measurable — no benign change moved any feature's output")
    args.json.write_text(json.dumps({"cases": rows}, indent=2))
    print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
