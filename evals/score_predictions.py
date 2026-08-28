#!/usr/bin/env python
"""Score any Blind Spot prediction against confirmed ground truth.

Deliberately shared between the baseline and the agent. One scorer, one metric
definition, one ground truth — so the comparison cannot drift, and neither side
can be flattered by a scoring change made after the fact.

    python evals/score_predictions.py baseline/predictions.json

Two errors, and they cost the user differently:

  A missed Blind Spot ships. The suite stays green, the model gets swapped, and
  the failure reaches production. This is the expensive one.

  A false Blind Spot wastes senior time. Someone investigates a hole that is not
  there and, worse, learns to distrust the tool.

Recall is therefore the headline. Precision is what stops recall being gamed by
answering "everything is a blind spot".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness  # noqa: E402


def prf(predicted: set[str], truth: set[str]) -> tuple[float, float, float]:
    tp = len(predicted & truth)
    precision = tp / len(predicted) if predicted else (1.0 if not truth else 0.0)
    recall = tp / len(truth) if truth else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions", type=Path)
    ap.add_argument("--json", type=Path, help="write the scored result here")
    args = ap.parse_args()

    doc = json.loads(args.predictions.read_text())
    cases = {c.name: c for c in harness.discover()}

    print(f"{doc['predictor']}  model={doc.get('model', '?')}  "
          f"verified={doc.get('verified')}")

    rows, all_pred, all_truth = [], set(), set()
    for name, predicted_list in doc["predictions"].items():
        case = cases[name]
        predicted, truth = set(predicted_list), case.known_blind_spots
        p, r, f1 = prf(predicted, truth)
        rows.append((name, p, r, f1))
        all_pred |= {f"{name}:{x}" for x in predicted}
        all_truth |= {f"{name}:{x}" for x in truth}

        print(f"\n{name}")
        print(f"  precision {p:.0%}   recall {r:.0%}   f1 {f1:.2f}")
        missed = sorted(truth - predicted)
        false_alarms = sorted(predicted - truth)
        if missed:
            print(f"  blind spots it did not find: {', '.join(missed)}")
        if false_alarms:
            print(f"  false alarms: {', '.join(false_alarms)}")
        bogus = doc.get("hallucinated_ids", {}).get(name) or []
        if bogus:
            print(f"  invented ids that do not exist: {', '.join(bogus)}")

    p, r, f1 = prf(all_pred, all_truth)
    print(f"\n{'=' * 52}")
    print(f"OVERALL   precision {p:.0%}   recall {r:.0%}   f1 {f1:.2f}")
    print(f"          found {len(all_pred & all_truth)}/{len(all_truth)} "
          f"confirmed blind spots")

    if args.json:
        args.json.write_text(json.dumps(
            {
                "predictor": doc["predictor"],
                "model": doc.get("model"),
                "verified": doc.get("verified"),
                "overall": {"precision": round(p, 4), "recall": round(r, 4),
                            "f1": round(f1, 4)},
                "per_case": [
                    {"case": n, "precision": round(a, 4), "recall": round(b, 4),
                     "f1": round(c, 4)} for n, a, b, c in rows
                ],
            }, indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
