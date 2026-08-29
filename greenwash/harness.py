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

from greenwash import observe, operators as ops

REPO_ROOT = Path(__file__).resolve().parent.parent


# A red suite proves nothing if the Harness itself is what broke. These are the
# signatures of our own machinery failing, and a Mutant that trips one is
# reported INVALID rather than counted as a kill.
HARNESS_FAULTS = (
    "FixtureMiss",
    "GREENWASH_FIXTURES is unset",
    "GREENWASH_MODE must be",
    "Unknown operator",
    "MissingVariant",
    "ModuleNotFoundError",
    "INTERNALERROR",
)


@dataclass
class MutantResult:
    operator: str
    summary: str
    killed: bool
    valid: bool = True
    inert: bool = False
    detail: str = ""

    @property
    def status(self) -> str:
        if not self.valid:
            return "INVALID"
        if self.inert:
            return "INERT"
        return "killed" if self.killed else "SURVIVED"


@dataclass
class CaseResult:
    case: str
    baseline_green: bool
    mutants: list[MutantResult]

    @property
    def scored(self) -> list[MutantResult]:
        """Only Mutants that ran and did something.

        Invalid ones are a bug in us. Inert ones are a sabotage that turned out
        not to sabotage anything — neither says a word about the Suite, and
        counting either would move the Kill Rate for no reason.
        """
        return [m for m in self.mutants if m.valid and not m.inert]

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

    @property
    def inert(self) -> list[str]:
        return [m.operator for m in self.mutants if m.valid and m.inert]


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
        # A case with no confirmed Blind Spots and a case nobody has checked are
        # both empty sets and mean opposite things. The precision control is the
        # first kind, and "not checked" would be the wrong thing to print for it.
        self.has_ground_truth: bool = gt.exists()
        self.known_blind_spots: set[str] = (
            set(json.loads(gt.read_text())["survivors"]) if gt.exists() else set()
        )

    def operators(self) -> list[ops.Operator]:
        return ops.applicable(self.tags)

    def run_suite(
        self,
        operator_id: str | None = None,
        select: str | None = None,
        fixtures: Path | None = None,
    ) -> tuple[bool, str]:
        """Run the case's pytest suite, optionally under one Operator.

        Returns (green, output). Green means every test passed.

        `select` narrows the run to one path inside the case. The Verification
        Gate uses it to judge a single Closing Test on its own: whether the rest
        of the Suite is green is already known and would only add noise.

        `fixtures` swaps in a different set of recorded answers. The brittleness
        probe uses it to replay a *second correct answer* from the same model,
        which is how a Closing Test that only accepts one exact wording gets
        caught.
        """
        env = {
            **os.environ,
            "GREENWASH_MODE": "replay",
            "GREENWASH_FIXTURES": str(fixtures or self.path / "fixtures"),
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


def evaluate_mutant(
    case: Case, op: ops.Operator, clean: list[dict] | None = None
) -> tuple[MutantResult, str, list[dict] | None]:
    """Apply one Operator, run the Suite, and work out what actually happened.

    Shared by the eval and the Auditor on purpose. If those two ever disagreed
    about what counts as a Survivor, one of this project's numbers would be a
    lie, and it would be the one on the front page.

    Three ways a green suite means nothing:

      the Harness broke      -> INVALID, we learned nothing
      the sabotage was a
      no-op on this Feature  -> INERT, there was nothing to catch
      neither                -> SURVIVED, and that is a Blind Spot

    Inertness is decided by running the case's Record Plan with and without the
    Operator. The Record Plan is every call the Suite makes, so if all of them
    come back identical, no assertion could have told the difference — this is
    the criterion itself, not an approximation of it. (A Suite that asserted on
    side effects rather than return values would need a different test.)
    """
    green, out = case.run_suite(op.id)
    fault = next((f for f in HARNESS_FAULTS if f in out), None)

    inert = False
    if green and fault is None:
        if clean is None:
            clean = observe.observe(case.path)
        mutated = observe.observe(case.path, op.id)
        inert = (
            not observe.failed(clean)
            and not observe.failed(mutated)
            and mutated == clean
        )

    result = MutantResult(
        operator=op.id,
        summary=op.summary,
        killed=not green and fault is None,
        valid=fault is None,
        inert=inert,
        detail=(
            f"harness fault: {fault}" if fault
            else "the feature returned exactly the same thing" if inert
            else "suite stayed green" if green
            else _first_failure(out)
        ),
    )
    return result, out, clean


def run_case(case: Case, verbose: bool = False) -> CaseResult:
    baseline_green, baseline_out = case.run_suite()
    if not baseline_green and verbose:
        print(f"  ! {case.name} is red before any mutation:\n{baseline_out}")

    mutants: list[MutantResult] = []
    clean: list[dict] | None = None
    for op in case.operators():
        result, _out, clean = evaluate_mutant(case, op, clean)
        mutants.append(result)
        if verbose:
            mark = {"INVALID": "!", "INERT": "-", "killed": "."}.get(result.status, "S")
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
