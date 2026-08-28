"""The Harness — runs a Corpus Case's suite once per Operator and counts.

The whole product rests on one loop:

    for each applicable Operator:
        sabotage the feature, run the case's own suite unchanged
        suite goes red  -> Killed    (the suite noticed)
        suite stays green -> Survivor (a Blind Spot, and here is the receipt)

Kill Rate is survivors subtracted from one. It is the number in the Trust
Report and the number the Improvement Changelog moves.

Each run is a fresh subprocess: a Patch mutates a live module, and letting that
leak between Operators would silently corrupt every later result.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from greenwash import operators as ops

REPO_ROOT = Path(__file__).resolve().parent.parent


# A red suite proves nothing if the Harness itself is what broke. These are the
# signatures of our own machinery failing, and a Mutant that trips one is
# reported INVALID rather than counted as a kill.
HARNESS_FAULTS = (
    "FixtureMiss",
    "GREENWASH_FIXTURES is unset",
    "GREENWASH_MODE must be",
    "Unknown operator",
    "ModuleNotFoundError",
    "INTERNALERROR",
)


@dataclass
class MutantResult:
    operator: str
    summary: str
    killed: bool
    valid: bool = True
    detail: str = ""

    @property
    def status(self) -> str:
        if not self.valid:
            return "INVALID"
        return "killed" if self.killed else "SURVIVED"


@dataclass
class CaseResult:
    case: str
    baseline_green: bool
    mutants: list[MutantResult]

    @property
    def scored(self) -> list[MutantResult]:
        """Only Mutants that actually ran. Invalid ones are a bug in us."""
        return [m for m in self.mutants if m.valid]

    @property
    def kill_rate(self) -> float:
        if not self.scored:
            return 0.0
        return sum(m.killed for m in self.scored) / len(self.scored)

    @property
    def survivors(self) -> list[str]:
        return [m.operator for m in self.scored if not m.killed]

    @property
    def invalid(self) -> list[str]:
        return [m.operator for m in self.mutants if not m.valid]


class Case:
    """One Corpus Case: an AI feature, its suite, and its known Blind Spots."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.name = self.path.name
        meta = json.loads((self.path / "case.json").read_text())
        self.tags: set[str] = set(meta["tags"])
        self.description: str = meta["description"]
        self.suite_looks_like: str = meta.get("suite_looks_like", "")
        gt = self.path / "blindspots.json"
        self.known_blind_spots: set[str] = (
            set(json.loads(gt.read_text())["survivors"]) if gt.exists() else set()
        )

    def operators(self) -> list[ops.Operator]:
        return ops.applicable(self.tags)

    def run_suite(
        self, operator_id: str | None = None, select: str | None = None
    ) -> tuple[bool, str]:
        """Run the case's pytest suite, optionally under one Operator.

        Returns (green, output). Green means every test passed.

        `select` narrows the run to one path inside the case. The Verification
        Gate uses it to judge a single Closing Test on its own: whether the rest
        of the Suite is green is already known and would only add noise.
        """
        env = {
            **os.environ,
            "GREENWASH_MODE": "replay",
            "GREENWASH_FIXTURES": str(self.path / "fixtures"),
            "PYTHONPATH": str(REPO_ROOT),
        }
        env.pop("GREENWASH_MODEL", None)
        if operator_id:
            env["GREENWASH_MUTATION"] = operator_id

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--no-header",
             "-p", "no:cacheprovider", *([select] if select else [])],
            cwd=self.path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return proc.returncode == 0, _stable((proc.stdout + proc.stderr)[-2000:])


# pytest prints its own wall clock, Python prints object addresses, and a
# traceback prints wherever this machine happens to keep its files. None of it
# is information, all of it differs between two identical runs, and the Auditor
# feeds this output straight back into its next prompt — so a Fixture recorded
# on one machine would miss on another and the whole replay claim would be
# false. Normalised where it is captured, once.
_NOISE = (
    (re.compile(r"\bin \d+\.\d+s\b"), "in N.NNs"),
    (re.compile(r"0x[0-9a-f]{6,}"), "0xADDR"),
    (re.compile(r"/(?:[\w.@+-]+/)+([\w.@+-]+/[\w.@+-]+\.py)"), r".../\1"),
)


def _stable(output: str) -> str:
    for pattern, replacement in _NOISE:
        output = pattern.sub(replacement, output)
    return output


def run_case(case: Case, verbose: bool = False) -> CaseResult:
    baseline_green, baseline_out = case.run_suite()
    if not baseline_green and verbose:
        print(f"  ! {case.name} is red before any mutation:\n{baseline_out}")

    mutants: list[MutantResult] = []
    for op in case.operators():
        green, out = case.run_suite(op.id)
        fault = next((f for f in HARNESS_FAULTS if f in out), None)
        # Green under sabotage means the suite never noticed: a Survivor.
        # Red for one of our own reasons means we learned nothing at all.
        result = MutantResult(
            operator=op.id,
            summary=op.summary,
            killed=not green and fault is None,
            valid=fault is None,
            detail=f"harness fault: {fault}" if fault
                   else ("" if green else _first_failure(out)),
        )
        mutants.append(result)
        if verbose:
            mark = "!" if not result.valid else ("." if result.killed else "S")
            print(f"  {mark} {op.id:28} {result.status}")

    return CaseResult(case=case.name, baseline_green=baseline_green, mutants=mutants)


def _first_failure(output: str) -> str:
    """The one line worth quoting as the receipt.

    pytest's `FAILED ...` summary names the test as well as the assertion, so it
    is preferred; a bare `E   ` line is the fallback for a collection error that
    never got as far as a summary.
    """
    lines = output.splitlines()
    for line in lines:
        if line.startswith("FAILED"):
            return line.strip()[:200]
    for line in lines:
        if line.startswith("E   "):
            return line.strip()[:200]
    return ""


def discover(corpus_dir: Path | None = None) -> list[Case]:
    corpus_dir = Path(corpus_dir or REPO_ROOT / "corpus")
    return [
        Case(p)
        for p in sorted(corpus_dir.iterdir())
        if p.is_dir() and (p / "case.json").exists()
    ]


def overlay(case: Case, extra_tests: dict[str, str], dest: Path) -> Case:
    """A scratch copy of a Corpus Case with extra test files dropped into `tests/`.

    A Suite is evidence. Closing Tests are therefore never written into one —
    they are merged onto a copy, and the copy is what gets measured. Fixtures
    come along, which is what keeps an Overlay offline and deterministic.
    """
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        case.path, dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache")
    )
    (dest / "tests").mkdir(exist_ok=True)
    for name, code in extra_tests.items():
        (dest / "tests" / name).write_text(code)
    return Case(dest)


def to_json(results: list[CaseResult]) -> str:
    return json.dumps(
        [
            {
                **asdict(r),
                "kill_rate": round(r.kill_rate, 4),
                "survivors": r.survivors,
            }
            for r in results
        ],
        indent=2,
    )
