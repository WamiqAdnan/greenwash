#!/usr/bin/env python
"""Record every model answer a Corpus Case needs, so the Harness can replay.

Run once per case, per model. Recording touches the GPU; replay never does.

    python scripts/record_fixtures.py --case 01_invoice_extractor
    python scripts/record_fixtures.py --case 01_invoice_extractor --model qwen3:0.6b

The weak model matters as much as the strong one: the `model.downgrade`
Operator swaps the feature onto it, and that Mutant cannot run without its own
recorded answers.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _run_plan(case_dir: Path, label: str, mutation: str | None) -> None:
    """Import the case fresh, optionally sabotage it, and make every call."""
    sys.path.insert(0, str(case_dir))
    for mod in ("feature", "record_plan", "tests", "tests.test_feature"):
        sys.modules.pop(mod, None)
    try:
        feature = importlib.import_module("feature")
        if mutation:
            from greenwash import operators as ops
            ops.get(mutation).patch(feature)
        plan = importlib.import_module("record_plan")
        for thunk in plan.CALLS:
            thunk()
        print(f"  {label}: {len(plan.CALLS)} call(s) recorded")
    finally:
        sys.path.remove(str(case_dir))


def record(case_dir: Path, model: str, with_mutations: bool = True) -> None:
    """Record the clean run, then one run per Operator that changes the prompt.

    A retrieval Operator rewrites the context the model sees, so it needs its
    own fixtures. Without them the Mutant dies of a fixture miss and the
    Harness reports INVALID — correct, but useless.
    """
    os.environ["GREENWASH_MODE"] = "record"
    os.environ["GREENWASH_FIXTURES"] = str(case_dir / "fixtures")
    os.environ["GREENWASH_MODEL"] = model

    if not (case_dir / "record_plan.py").exists():
        raise SystemExit(
            f"{case_dir.name} has no record_plan.py — it must list every call "
            f"the suite will make, so replay never misses."
        )

    import json as _json
    from greenwash import operators as ops

    tags = set(_json.loads((case_dir / "case.json").read_text())["tags"])
    print(f"{case_dir.name} @ {model}")
    _run_plan(case_dir, "clean", None)

    if not with_mutations:
        return
    # Only Operators that alter what reaches the model need extra fixtures.
    for op in ops.applicable(tags):
        if not op.id.startswith(("retrieval.",)):
            continue
        os.environ["GREENWASH_MODEL"] = model
        _run_plan(case_dir, op.id, op.id)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--no-mutations", action="store_true",
                    help="skip the extra prompt-changing Operator runs")
    args = ap.parse_args()
    record(ROOT / "corpus" / args.case, args.model,
           with_mutations=not args.no_mutations)


if __name__ == "__main__":
    main()
