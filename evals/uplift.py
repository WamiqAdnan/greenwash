#!/usr/bin/env python
"""Kill Rate before the Auditor's Closing Tests, and after. The user's number.

Kill Rate says how blind a Suite is. Uplift says how much of that the Auditor
actually closed, which is the thing the engineer who owns the feature is
deciding on.

    .venv/bin/python evals/uplift.py
    .venv/bin/python evals/uplift.py --case 03_rag_citations -v

Measured here, outside the agent, from the Closing Tests committed under
`auditor/closing_tests/`. The agent never scores itself.

Suites are evidence, so nothing is edited: Closing Tests are merged onto an
**Overlay** — a scratch copy of the Corpus Case, fixtures and all — and the
Overlay is what gets run.

## The guard, and why it is here

A Closing Test that trips a `HARNESS_FAULTS` signature under some *other*
Operator turns that Mutant INVALID, and Invalid Mutants leave the denominator.
Kill Rate would then rise because a Mutant stopped being measurable, not because
anything was detected. That is the bug that once cost this project 17 points,
wearing a new hat. So: any Mutant that was valid before the merge and invalid
after it means the uplift for that case is **not reported**.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auditor.agent import CLOSING_TEST_FILE, DEFAULT_SCRATCH  # noqa: E402
from greenwash import harness  # noqa: E402

CLOSING = ROOT / "auditor" / "closing_tests"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", type=Path, default=ROOT / "evals" / "uplift.json")
    args = ap.parse_args()

    cases = harness.discover()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            raise SystemExit(f"no such case: {args.case}")

    rows = []
    for case in cases:
        print(f"\n{case.name}")
        before = harness.run_case(case, verbose=args.verbose)

        path = CLOSING / f"{case.name}.py"
        code = path.read_text() if path.exists() else ""
        if "def test_" not in code:
            print("  no closing tests — nothing to merge")
            rows.append({"case": case.name, "before": round(before.kill_rate, 4),
                         "after": round(before.kill_rate, 4), "closed": [],
                         "reported": True, "note": "no closing tests"})
            continue

        merged = harness.overlay(
            case, {CLOSING_TEST_FILE: code}, DEFAULT_SCRATCH / case.name / "merged"
        )
        if args.verbose:
            print("  --- with closing tests merged ---")
        after = harness.run_case(merged, verbose=args.verbose)

        new_invalid = sorted(set(after.invalid) - set(before.invalid))
        if not after.baseline_green:
            print("  ! the merged suite is RED on the clean feature — "
                  "these closing tests are broken, uplift not reported")
            rows.append({"case": case.name, "before": round(before.kill_rate, 4),
                         "after": None, "closed": [], "reported": False,
                         "note": "merged suite red on the clean feature"})
            continue
        if new_invalid:
            print(f"  ! a closing test made these mutants INVALID: "
                  f"{', '.join(new_invalid)}")
            print("    an invalid mutant leaves the denominator, so this would "
                  "raise the kill rate without detecting anything. Not reported.")
            rows.append({"case": case.name, "before": round(before.kill_rate, 4),
                         "after": None, "closed": [], "reported": False,
                         "note": f"new invalid mutants: {new_invalid}"})
            continue

        closed = sorted(set(before.survivors) - set(after.survivors))
        still_open = sorted(set(after.survivors))
        print(f"  kill rate {before.kill_rate:.0%} -> {after.kill_rate:.0%}   "
              f"({len(closed)} of {len(before.survivors)} blind spots closed)")
        if closed:
            print(f"  closed: {', '.join(closed)}")
        if still_open:
            print(f"  still blind: {', '.join(still_open)}")
        rows.append({"case": case.name, "before": round(before.kill_rate, 4),
                     "after": round(after.kill_rate, 4), "closed": closed,
                     "still_open": still_open, "reported": True})

    reported = [r for r in rows if r["reported"] and r["after"] is not None]
    print(f"\n{'=' * 52}")
    if reported:
        b = sum(r["before"] for r in reported) / len(reported)
        a = sum(r["after"] for r in reported) / len(reported)
        print(f"corpus mean kill rate  {b:.0%} -> {a:.0%}   "
              f"({len(reported)} of {len(rows)} case(s) reported)")
        # A case with no Blind Spots has none to close and can only pull the
        # mean towards itself. Both numbers are shown so neither can be quoted
        # as if it were the other.
        movable = [r for r in reported if r["before"] < 1.0]
        if movable and len(movable) != len(reported):
            mb = sum(r["before"] for r in movable) / len(movable)
            ma = sum(r["after"] for r in movable) / len(movable)
            print(f"  of which had blind spots to close: {mb:.0%} -> {ma:.0%}   "
                  f"({len(movable)} case(s))")
    else:
        print("nothing reportable")
    unreported = [r for r in rows if not r["reported"]]
    if unreported:
        print(f"! not reported: {', '.join(r['case'] for r in unreported)}")

    args.json.write_text(json.dumps({"cases": rows}, indent=2))
    print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
