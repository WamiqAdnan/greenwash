#!/usr/bin/env python
"""The baseline: ask a model to predict Blind Spots, with no way to check.

The fairness of this comparison is the whole point, so it is worth being
explicit about how the baseline is *helped*:

  - It sees the same feature code and the same suite the agent will see.
  - It sees the full Operator catalogue, with ids and summaries. It does not
    have to invent the vocabulary or guess what counts as a failure.
  - It answers in the same format the agent answers in, so one scorer measures
    both.
  - It is asked exactly the question the agent is asked.

The one thing it cannot do is run anything. That is the only variable under
test: **prediction versus verification**. A baseline starved of context would
be easy to beat and would prove nothing; this one should be hard to beat, and
if it is not beaten, that is a real result about the product.

    python baseline/predict.py --model qwen3:8b -o baseline/predictions.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness, operators as ops  # noqa: E402
from greenwash.modelclient import _call_ollama  # noqa: E402

PROMPT = """You are reviewing whether a test suite is worth trusting.

Below is an AI-backed feature and the test suite that guards it. Then a list of
sabotages that could be applied to the feature.

For each sabotage, decide: if someone applied it, would this test suite FAIL
(catch it) or PASS (miss it)?

## The feature

```python
{feature}
```

## The test suite

```python
{tests}
```

## The sabotages

{catalogue}

## Your answer

Reply with JSON only. List the ids of every sabotage this suite would MISS —
the ones where the tests would still pass even though the feature is broken.

{{"missed": ["sabotage.id", ...]}}

JSON:"""


def build_prompt(case: harness.Case) -> str:
    feature = (case.path / "feature.py").read_text()
    tests = (case.path / "tests" / "test_feature.py").read_text()
    catalogue = "\n".join(
        f"- `{op.id}` — {op.summary}" for op in case.operators()
    )
    return PROMPT.format(feature=feature, tests=tests, catalogue=catalogue)


def parse(raw: str, valid: set[str]) -> tuple[list[str], list[str]]:
    """Return (predicted ids that exist, hallucinated ids that do not)."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return [], []
    try:
        missed = json.loads(match.group(0)).get("missed", [])
    except json.JSONDecodeError:
        return [], []
    missed = [m for m in missed if isinstance(m, str)]
    return [m for m in missed if m in valid], [m for m in missed if m not in valid]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "baseline" / "predictions.json")
    ap.add_argument("--case", help="limit to one case")
    args = ap.parse_args()

    cases = harness.discover()
    if args.case:
        cases = [c for c in cases if c.name == args.case]

    predictions, hallucinated, raws = {}, {}, {}
    for case in cases:
        valid = {op.id for op in case.operators()}
        prompt = build_prompt(case)
        print(f"{case.name}: asking {args.model} about {len(valid)} sabotages...")
        raw = _call_ollama(args.model, prompt)
        predicted, bogus = parse(raw, valid)
        predictions[case.name] = predicted
        hallucinated[case.name] = bogus
        raws[case.name] = raw
        print(f"  predicted missed: {predicted or '(none)'}")
        if bogus:
            print(f"  ! invented sabotage ids that do not exist: {bogus}")

    args.out.write_text(
        json.dumps(
            {
                "predictor": "baseline-oneshot",
                "model": args.model,
                "verified": False,
                "predictions": predictions,
                "hallucinated_ids": hallucinated,
                "raw": raws,
            },
            indent=2,
        )
    )
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
