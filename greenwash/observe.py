"""Show what a Feature actually returns, clean or sabotaged.

The Auditor has to write assertions about a Feature it has never watched run.
Asking a model to imagine the return value is exactly the guessing this project
exists to remove, so we hand it the real one instead.

A Corpus Case already lists every call its Suite makes — that is what a Record
Plan is for. This runs the plan under replay and reports what came back, with
and without an Operator applied.

    python -m greenwash.observe corpus/01_invoice_extractor
    python -m greenwash.observe corpus/01_invoice_extractor --operator value.zero_amounts

Runs as a subprocess for the same reason every Mutant does: a Patch mutates a
live module, and letting that leak would corrupt whatever ran next.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _call_source(thunk) -> str:
    """The call as the Record Plan writes it, plus whatever it was bound to.

    A plan built by comprehension (`[lambda q=q: answer(q) for q in QUESTIONS]`)
    has one source line and many calls, so the bound default is the only thing
    that tells the observations apart.
    """
    try:
        src = inspect.getsource(thunk).strip().rstrip(",")
    except (OSError, TypeError):
        src = getattr(thunk, "__name__", repr(thunk))
    if "lambda" in src:
        src = src[src.index("lambda"):].rstrip("]").rstrip()
        src = re.sub(r"\s+for\s+\w+\s+in\s+\w+$", "", src)
    code = getattr(thunk, "__code__", None)
    defaults = getattr(thunk, "__defaults__", None) or ()
    if code and defaults:
        names = code.co_varnames[code.co_argcount - len(defaults):code.co_argcount]
        bound = ", ".join(f"{n}={v!r}" for n, v in zip(names, defaults))
        src = f"{src}   with {bound}"
    return src


def _render(value) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def observe_in_process(case_dir: Path, operator_id: str | None) -> list[dict]:
    sys.path.insert(0, str(case_dir))
    for mod in ("feature", "record_plan", "tests", "tests.test_feature"):
        sys.modules.pop(mod, None)
    try:
        feature = importlib.import_module("feature")
        if operator_id:
            from greenwash import operators as ops

            ops.get(operator_id).patch(feature)
        plan = importlib.import_module("record_plan")
        out = []
        for i, thunk in enumerate(plan.CALLS):
            record = {"call": i, "source": _call_source(thunk)}
            try:
                record["returned"] = _render(thunk())
            except Exception as exc:  # the Feature raising is itself an observation
                record["raised"] = f"{type(exc).__name__}: {exc}"[:300]
            out.append(record)
        return out
    finally:
        sys.path.remove(str(case_dir))


def observe(case_dir: Path, operator_id: str | None = None) -> list[dict]:
    """What the Feature returns, from a fresh subprocess."""
    argv = [sys.executable, "-m", "greenwash.observe", str(case_dir), "--json"]
    if operator_id:
        argv += ["--operator", operator_id]
    proc = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        return [{"call": -1, "source": "(observation failed)",
                 "raised": (proc.stdout + proc.stderr)[-400:]}]
    return json.loads(proc.stdout)


def as_text(observations: list[dict]) -> str:
    lines = []
    for o in observations:
        lines.append(f"call {o['call'] + 1}: {o['source']}")
        if "returned" in o:
            lines.append(f"  returned {o['returned'][:700]}")
        else:
            lines.append(f"  raised   {o['raised']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", type=Path)
    ap.add_argument("--operator")
    ap.add_argument("--json", action="store_true", help="machine-readable, for the Auditor")
    args = ap.parse_args()

    case_dir = args.case if args.case.is_absolute() else REPO_ROOT / args.case
    os.environ.setdefault("GREENWASH_MODE", "replay")
    os.environ["GREENWASH_FIXTURES"] = str(case_dir / "fixtures")
    os.environ.pop("GREENWASH_MODEL", None)

    observations = observe_in_process(case_dir, args.operator)
    print(json.dumps(observations, indent=None) if args.json else as_text(observations))


if __name__ == "__main__":
    main()
