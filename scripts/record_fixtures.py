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
        # `CALLS` is the Record Plan proper — exactly what the Suite calls, and
        # what the Inert check compares. `EXTRA_CALLS` is anything else that has
        # to be on disk for an offline replay: today, the held-out tickets
        # `evals/leakage.py` needs. They are recorded and never observed, which
        # is what keeps "the Suite could not have noticed" a true statement.
        calls = list(plan.CALLS) + list(getattr(plan, "EXTRA_CALLS", []))
        for thunk in calls:
            thunk()
        print(f"  {label}: {len(calls)} call(s) recorded")
    finally:
        sys.path.remove(str(case_dir))


def record(case_dir: Path, model: str, with_mutations: bool = True,
           into: str = "fixtures", temperature: float = 0.0) -> None:
    """Record the clean run, then one run per Operator that changes the prompt.

    A retrieval Operator rewrites the context the model sees, so it needs its
    own fixtures. Without them the Mutant dies of a fixture miss and the
    Harness reports INVALID — correct, but useless.
    """
    os.environ["GREENWASH_MODE"] = "record"
    os.environ["GREENWASH_FIXTURES"] = str(case_dir / into)
    os.environ["GREENWASH_MODEL"] = model
    os.environ["GREENWASH_TEMPERATURE"] = str(temperature)

    if not (case_dir / "record_plan.py").exists():
        raise SystemExit(
            f"{case_dir.name} has no record_plan.py — it must list every call "
            f"the suite will make, so replay never misses."
        )

    import json as _json
    from greenwash import operators as ops

    tags = set(_json.loads((case_dir / "case.json").read_text())["tags"])
    print(f"{case_dir.name} @ {model} -> {into}/ (temperature {temperature})")
    _run_plan(case_dir, "clean", None)

    if not with_mutations:
        return
    # Anything that alters what reaches the model needs its own fixtures, or its
    # Mutant dies of a fixture miss and reports INVALID. That is the retrieval
    # Operators, which rewrite the context, and every Benign Change, which
    # rewrites the prompt itself.
    changes_the_prompt = [
        op for op in ops.applicable(tags) if op.id.startswith("retrieval.")
    ] + ops.applicable_benign(tags)
    for op in changes_the_prompt:
        os.environ["GREENWASH_MODEL"] = model
        _run_plan(case_dir, op.id, op.id)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--no-mutations", action="store_true",
                    help="skip the extra prompt-changing Operator runs")
    ap.add_argument("--into", default="fixtures",
                    help="directory under the case to write into")
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="0 for everything Greenwash measures; higher only for "
                         "the brittleness probe's second correct answer")
    args = ap.parse_args()
    record(ROOT / "corpus" / args.case, args.model,
           with_mutations=not args.no_mutations,
           into=args.into, temperature=args.temperature)


if __name__ == "__main__":
    main()
