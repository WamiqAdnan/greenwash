#!/usr/bin/env python
"""Accuracy on the examples that are in the prompt, against accuracy on examples
that are not.

This is the measurement Greenwash cannot make, and the reason `10_few_shot_leak`
is in the corpus.

Mutation testing asks one question: if the feature breaks, does the suite go red?
For case 10 the answer is yes, every time, for every sabotage. Kill Rate 100%,
no Blind Spots, and the Trust Report says the suite is in good shape. That answer
is *correct* — and the suite is still worthless, because its five test cases are
the five few-shot examples in the prompt. It measures whether the model can
repeat what it was just shown.

No Operator can find this. A sabotage that breaks the feature breaks it on the
in-prompt examples too, so the suite notices, so the suite looks good. The flaw
is not in what the suite fails to catch; it is in what the suite is *made of*.
Every technique in this project is blind to it by construction, and saying so is
worth more than pretending otherwise.

What does find it is holding examples back:

    .venv/bin/python evals/leakage.py

A case opts in by declaring `EXAMPLES` (in the prompt, and tested) and `HELDOUT`
(neither) in its `feature.py`, both mapping an id to `(text, expected_label)`.
The held-out calls go in `EXTRA_CALLS` rather than the Record Plan proper, so
they are recorded and replay offline without ever entering the Inert comparison
— "the Suite could not have noticed" has to stay a true statement.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness  # noqa: E402


def _predict(case_dir: Path, operator: str | None = None) -> dict:
    """Run the feature over both sets, in a subprocess, under replay."""
    argv = [sys.executable, "-m", "evals.leakage", "--predict", str(case_dir)]
    if operator:
        argv += ["--operator", operator]
    proc = subprocess.run(
        argv, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        return {"error": (proc.stdout + proc.stderr)[-400:]}
    return json.loads(proc.stdout)


def _predict_here(case_dir: Path, operator: str | None = None) -> dict:
    sys.path.insert(0, str(case_dir))
    os.environ.setdefault("GREENWASH_MODE", "replay")
    os.environ["GREENWASH_FIXTURES"] = str(case_dir / "fixtures")
    os.environ.pop("GREENWASH_MODEL", None)
    import importlib

    feature = importlib.import_module("feature")
    if operator:
        from greenwash import operators as ops

        ops.get(operator).patch(feature)
    out = {"in_prompt": {}, "held_out": {}}
    for bucket, source in (("in_prompt", feature.EXAMPLES),
                           ("held_out", feature.HELDOUT)):
        for ticket_id, (_text, expected) in source.items():
            try:
                got = feature.classify(ticket_id)["label"]
            except Exception as exc:  # a broken prediction is still a result
                got = f"<{type(exc).__name__}>"
            out[bucket][ticket_id] = {"expected": expected, "got": got}
    return out


def _score(bucket: dict) -> tuple[int, int]:
    right = sum(1 for r in bucket.values() if r["got"] == r["expected"])
    return right, len(bucket)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predict", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--operator", help=argparse.SUPPRESS)
    ap.add_argument("--json", type=Path, default=ROOT / "evals" / "leakage.json")
    args = ap.parse_args()

    if args.predict:
        print(json.dumps(_predict_here(args.predict, args.operator)))
        return

    rows = []
    for case in harness.discover():
        src = (case.path / "feature.py").read_text()
        if "HELDOUT" not in src or "EXAMPLES" not in src:
            continue
        print(f"\n{case.name}")
        row = {"case": case.name, "runs": {}}
        # The clean feature, and the same feature with the model swapped for a
        # much weaker one. The Suite cannot tell those two apart — Greenwash
        # reports `model.downgrade` here as Inert, which is literally true and
        # is the whole problem.
        for label, operator in (("as shipped", None),
                                ("under model.downgrade", "model.downgrade")):
            result = _predict(case.path, operator)
            if "error" in result:
                print(f"  {label}: could not run: {result['error']}")
                continue
            in_right, in_total = _score(result["in_prompt"])
            out_right, out_total = _score(result["held_out"])
            gap = ((in_right / in_total) - (out_right / out_total)
                   if in_total and out_total else 0)
            print(f"  {label}")
            print(f"    in the prompt : {in_right}/{in_total}   "
                  f"— these are the suite's test cases, so this is what it scores")
            print(f"    held out      : {out_right}/{out_total}   "
                  f"— the suite has never seen these")
            for ticket_id, r in result["held_out"].items():
                if r["got"] != r["expected"]:
                    print(f"      {ticket_id}: expected {r['expected']!r}, "
                          f"got {r['got']!r}")
            row["runs"][label] = {
                "in_prompt": [in_right, in_total],
                "held_out": [out_right, out_total],
                "gap": round(gap, 4),
                "detail": result,
            }
        rows.append(row)

    print(f"\n{'=' * 52}")
    if not rows:
        print("no case declares a held-out set")
    for row in rows:
        shipped = row["runs"].get("as shipped", {})
        weak = row["runs"].get("under model.downgrade", {})
        if not shipped or not weak:
            continue
        si, sit = shipped["in_prompt"]
        wi, wit = weak["in_prompt"]
        wh, wht = weak["held_out"]
        print(f"{row['case']}: the suite scores {si}/{sit} as shipped and "
              f"{wi}/{wit} with the model swapped for one 13x smaller, so it "
              f"cannot tell them apart. On tickets it has never seen, the small "
              f"model gets {wh}/{wht}.")
        print("Kill Rate cannot find this. Every sabotage breaks the in-prompt "
              "examples too, so the suite goes red and looks healthy.")
    args.json.write_text(json.dumps({"cases": rows}, indent=2))
    print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
