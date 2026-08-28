#!/usr/bin/env python
"""Measure the Kill Rate of every Corpus Case, and check it against ground truth.

This is the evaluation the Improvement Changelog reports against. It runs the
Harness over the corpus and, where a case declares its Blind Spots, reports
whether the measured Survivors are the ones we intended to build in.

A mismatch is a finding, not a nuisance: either the suite is stronger than we
thought, or an Operator does not bite the way we assumed.

    python evals/run_eval.py                     # whole corpus
    python evals/run_eval.py --case 01_invoice_extractor -v
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="run a single case by directory name")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", type=Path, help="write full results here")
    args = ap.parse_args()

    cases = harness.discover()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            raise SystemExit(f"no such case: {args.case}")

    results = []
    for case in cases:
        print(f"\n{case.name}  [{', '.join(sorted(case.tags))}]")
        result = harness.run_case(case, verbose=args.verbose)
        results.append(result)

        if not result.baseline_green:
            print("  ! suite is red before mutation — fix before trusting anything below")

        killed = sum(m.killed for m in result.scored)
        print(
            f"  kill rate: {result.kill_rate:.0%} "
            f"({killed}/{len(result.scored)} mutants killed)"
        )
        if result.invalid:
            print(f"  ! INVALID (harness fault, not scored): {', '.join(result.invalid)}")
        if result.survivors:
            print(f"  blind spots: {', '.join(result.survivors)}")

        expected = case.known_blind_spots
        if expected:
            measured = set(result.survivors)
            if measured == expected:
                print("  ground truth: matches")
            else:
                missing = expected - measured
                extra = measured - expected
                print("  ground truth: MISMATCH")
                if missing:
                    print(f"    expected to survive but was killed: {sorted(missing)}")
                if extra:
                    print(f"    survived unexpectedly: {sorted(extra)}")

    if results:
        overall = sum(r.kill_rate for r in results) / len(results)
        print(f"\ncorpus mean kill rate: {overall:.0%}  ({len(results)} case(s))")

    if args.json:
        args.json.write_text(harness.to_json(results))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
