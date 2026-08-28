"""The Auditor — the agent this project exists to build.

The bet the whole submission rests on: **the Auditor never predicts.** The
Baseline reads a Feature and a Suite and guesses which sabotages would slip
past. That is hard, and a local 8B model measurably fails at it. The Auditor
does not guess. It applies an Operator, runs the Suite, and reads the result.
Verification does the work that intelligence would otherwise have to do.

So the model is left with the one job that genuinely needs a model: given a
Survivor and the values the Feature actually returned, write the assertion that
would have caught it. And even there it is not trusted — every Closing Test it
writes must pass the **Verification Gate** (green clean, red under the Mutant)
or it goes back with the pytest output attached. A bad assertion from a small
model dies in the Gate instead of reaching the user.

Four phases per Corpus Case:

  triage      the model orders the Operator catalogue and records a Prior
  verify      the Harness runs them; Survivors come out with receipts
  remediate   the model writes a Closing Test per Survivor, the Gate judges it,
              rejects go back with the real failure output
  report      predictions.json, Closing Tests, a Trust Report, a Trajectory

Nothing here scores itself. Uplift is measured by `evals/uplift.py`.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from greenwash import harness, observe
from greenwash.modelclient import record_or_replay

REPO_ROOT = Path(__file__).resolve().parent.parent
CLOSING_TEST_FILE = "test_greenwash_closing.py"
DEFAULT_SCRATCH = Path(tempfile.gettempdir()) / "greenwash-scratch"


# ---------------------------------------------------------------------------
# The instructions that shape the agent. Quoted into every Trajectory header,
# because a trace you cannot read the instructions from is not a trace.
# ---------------------------------------------------------------------------

INSTRUCTIONS = """You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates."""


TRIAGE = """{instructions}

## The feature

```python
{feature}
```

## The suite that guards it

```python
{tests}
```

## The sabotages available for this feature

{catalogue}

## Your task

Order the sabotages, most likely to slip past this suite first. Then say which
you expect it to miss. You will find out; this is recorded so we can compare
what you expected with what actually happened.

Reply with JSON only:

{{"order": ["sabotage.id", ...], "expect_missed": ["sabotage.id", ...], "why": "one sentence"}}

JSON:"""


WRITE_CLOSING_TEST = """{instructions}

## The feature

```python
{feature}
```

## The suite that missed this

```python
{tests}
```

## What was done to the feature

`{operator}` — {summary}

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

{clean}

After `{operator}`:

{mutated}

## Your task

Write ONE pytest test that FAILS after `{operator}` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:"""


REVISE_CLOSING_TEST = """{instructions}

## What you wrote

```python
{code}
```

## What happened when it was run

{verdict}

```
{output}
```

## What the feature actually returns

Before `{operator}`:

{clean}

After `{operator}`:

{mutated}

## Your task

Fix it. It must PASS on the clean feature and FAIL after `{operator}`.
Reply with Python only, the whole test, no explanation, no markdown fences.

Python:"""


# ---------------------------------------------------------------------------
# The Verification Gate
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    accepted: bool
    clean_green: bool
    kills_mutant: bool
    reason: str
    failure_line: str = ""
    output: str = ""

    def as_line(self) -> str:
        return ("accepted" if self.accepted else "rejected") + f": {self.reason}"


class VerificationGate:
    """Two runs, and a Closing Test only counts if it survives both.

    Green on the clean Feature, red under the Mutant it claims to close, and
    neither run tripping a `HARNESS_FAULTS` signature — a Closing Test that
    fails because a fixture is missing has demonstrated nothing.

    Both runs happen on an Overlay. The Suite is evidence and is never edited.
    """

    def __init__(self, case: harness.Case, scratch: Path = DEFAULT_SCRATCH):
        self.case = case
        self.dest = Path(scratch) / case.name / "candidate"

    def judge(self, operator_id: str, code: str) -> Verdict:
        problem = _unrunnable(code)
        if problem:
            return Verdict(False, False, False, reason=f"not runnable: {problem}")

        candidate = harness.overlay(self.case, {CLOSING_TEST_FILE: code}, self.dest)
        select = f"tests/{CLOSING_TEST_FILE}"

        clean_green, clean_out = candidate.run_suite(select=select)
        fault = _fault(clean_out)
        if fault or not clean_green:
            return Verdict(
                False, False, False,
                reason=f"red on the clean feature ({fault or 'assertion failed'})",
                output=clean_out,
            )

        mutant_green, mutant_out = candidate.run_suite(operator_id, select=select)
        fault = _fault(mutant_out)
        if fault:
            return Verdict(
                False, True, False,
                reason=f"harness fault under {operator_id}, so it proves nothing: {fault}",
                output=mutant_out,
            )
        if mutant_green:
            return Verdict(
                False, True, False,
                reason=f"{operator_id} was applied and the test still passed",
                output=mutant_out,
            )
        return Verdict(
            True, True, True,
            reason=f"green on the clean feature, red under {operator_id}",
            failure_line=harness._first_failure(mutant_out),
            output=mutant_out,
        )


def _fault(output: str) -> str | None:
    return next((f for f in harness.HARNESS_FAULTS if f in output), None)


def _unrunnable(code: str) -> str:
    """Cheap rejections, so an obvious miss costs no subprocess."""
    if "def test_" not in code:
        return "no test function"
    try:
        compile(code, "<closing test>", "exec")
    except SyntaxError as exc:
        return f"syntax error, line {exc.lineno}: {exc.msg}"
    return ""


# ---------------------------------------------------------------------------
# The Trajectory
# ---------------------------------------------------------------------------

class Trajectory:
    """Every prompt, every tool call, every observation, in order.

    A required deliverable, and the only honest way to show how a finding was
    arrived at. Deliberately timestamp-free: replaying a recorded audit rewrites
    this file byte for byte, which is a reproducibility claim a judge can check
    with `git diff`.
    """

    def __init__(self, path: Path, header: dict):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.step = 0
        self.path.write_text("")
        self.event("start", "header", **header)

    def event(self, phase: str, kind: str, **fields) -> None:
        self.step += 1
        record = {"step": self.step, "phase": phase, "kind": kind, **fields}
        with self.path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------

class Model:
    """The Auditor's own record/replay seam.

    An audit a judge cannot re-run offline is not a reproducible result, so the
    Auditor's own model answers are Fixtures too.
    """

    def __init__(self, name: str, fixture_dir: Path, mode: str, trajectory: Trajectory):
        self.name = name
        self.fixture_dir = Path(fixture_dir)
        self.mode = mode
        self.trajectory = trajectory

    def ask(self, phase: str, prompt: str) -> str:
        self.trajectory.event(phase, "prompt", model=self.name, text=prompt)
        raw = record_or_replay(
            prompt,
            model=self.name,
            fixture_dir=self.fixture_dir,
            mode=self.mode,
            hint="Re-record with: python auditor/audit.py --record",
        )
        self.trajectory.event(phase, "response", model=self.name, text=raw)
        return raw


# ---------------------------------------------------------------------------
# The tools
# ---------------------------------------------------------------------------

class Tools:
    """Everything the Auditor is allowed to do.

    Every method logs its call and its result to the Trajectory, so the trace is
    a by-product of the agent working rather than a story written afterwards.
    """

    def __init__(self, case: harness.Case, trajectory: Trajectory, scratch: Path):
        self.case = case
        self.trajectory = trajectory
        self.gate = VerificationGate(case, scratch)
        self._observations: dict[str | None, str] = {}
        self._clean_raw: list[dict] | None = None

    def _log(self, phase: str, name: str, args: dict, result: str) -> None:
        self.trajectory.event(phase, "tool_call", tool=name, args=args)
        self.trajectory.event(phase, "tool_result", tool=name, text=result)

    def read_feature(self, phase: str = "triage") -> str:
        src = (self.case.path / "feature.py").read_text()
        self._log(phase, "read_feature", {"case": self.case.name}, src)
        return src

    def read_suite(self, phase: str = "triage") -> str:
        src = (self.case.path / "tests" / "test_feature.py").read_text()
        self._log(phase, "read_suite", {"case": self.case.name}, src)
        return src

    def list_operators(self, phase: str = "triage") -> list:
        ops_ = self.case.operators()
        catalogue = "\n".join(f"- `{op.id}` — {op.summary}" for op in ops_)
        self._log(phase, "list_operators", {"tags": sorted(self.case.tags)}, catalogue)
        return ops_

    def observe(self, operator_id: str | None = None, phase: str = "remediate") -> str:
        if operator_id not in self._observations:
            self._observations[operator_id] = observe.as_text(
                observe.observe(self.case.path, operator_id)
            )
        text = self._observations[operator_id]
        self._log(phase, "observe", {"operator": operator_id}, text)
        return text

    def run_operator(self, op) -> harness.MutantResult:
        """Apply one Operator and read what happened, using the eval's own judge.

        Deliberately `harness.evaluate_mutant` rather than the Auditor's own
        opinion: the agent and the number it is measured against must agree on
        what a Survivor is.
        """
        result, out, self._clean_raw = harness.evaluate_mutant(
            self.case, op, self._clean_raw
        )
        self._log(
            "verify", "run_operator", {"operator": op.id},
            f"{result.status} — {result.detail}\n{out[-600:]}",
        )
        return result

    def propose_closing_test(self, operator_id: str, code: str) -> Verdict:
        verdict = self.gate.judge(operator_id, code)
        self._log(
            "remediate", "propose_closing_test",
            {"operator": operator_id, "code": code},
            f"{verdict.as_line()}\n{verdict.output[-600:]}",
        )
        return verdict


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A Survivor, with the run that proves it and the test that closes it."""

    operator: str
    summary: str
    receipt: str
    closing_test: str = ""
    closing_test_failure: str = ""
    attempts: int = 0
    gate: str = "no closing test accepted"

    @property
    def closed(self) -> bool:
        return bool(self.closing_test)


@dataclass
class AuditResult:
    case: str
    kill_rate_before: float
    findings: list[Finding] = field(default_factory=list)
    killed: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)
    prior: dict = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    inert: list[str] = field(default_factory=list)

    @property
    def survivors(self) -> list[str]:
        return [f.operator for f in self.findings]


def audit_case(
    case: harness.Case,
    model: Model,
    trajectory: Trajectory,
    scratch: Path = DEFAULT_SCRATCH,
    max_attempts: int = 3,
    budget: int | None = None,
    log=print,
) -> AuditResult:
    tools = Tools(case, trajectory, scratch)

    # --- triage -------------------------------------------------------------
    feature = tools.read_feature()
    tests = tools.read_suite()
    operators = tools.list_operators()
    catalogue = "\n".join(f"- `{op.id}` — {op.summary}" for op in operators)

    raw = model.ask("triage", TRIAGE.format(
        instructions=INSTRUCTIONS, feature=feature, tests=tests, catalogue=catalogue,
    ))
    prior = _parse_prior(raw, {op.id for op in operators})
    trajectory.event("triage", "decision", prior=prior)
    log(f"  prior: expects to miss {prior['expect_missed'] or '(nothing)'}")

    ordered = _order(operators, prior["order"])
    if budget:
        # The ordering only earns its keep under a budget; the default is to run
        # the whole applicable catalogue, because the Harness is cheap and a
        # Blind Spot the Auditor never ran for is a Blind Spot it cannot report.
        ordered, deferred = ordered[:budget], ordered[budget:]
    else:
        deferred = []

    # --- verify -------------------------------------------------------------
    result = AuditResult(
        case=case.name, kill_rate_before=0.0, prior=prior,
        skipped=[op.id for op in deferred],
    )
    scored = []
    for op in ordered:
        mutant = tools.run_operator(op)
        if not mutant.valid:
            result.invalid.append(op.id)
            log(f"  ! {op.id:28} INVALID — {mutant.detail}")
            continue
        if mutant.inert:
            # The suite stayed green because there was nothing to notice. Not a
            # finding, and reporting it would be the false alarm that costs the
            # user their trust in the tool.
            result.inert.append(op.id)
            log(f"  - {op.id:28} INERT — {mutant.detail}")
            continue
        scored.append(mutant)
        if mutant.killed:
            result.killed.append(op.id)
            log(f"  . {op.id:28} killed")
        else:
            result.findings.append(
                Finding(operator=op.id, summary=op.summary, receipt=mutant.detail)
            )
            log(f"  S {op.id:28} SURVIVED")
    result.kill_rate_before = (
        sum(m.killed for m in scored) / len(scored) if scored else 0.0
    )

    # --- remediate ----------------------------------------------------------
    clean = tools.observe(None)
    for finding in result.findings:
        mutated = tools.observe(finding.operator)
        prompt = WRITE_CLOSING_TEST.format(
            instructions=INSTRUCTIONS, feature=feature, tests=tests,
            operator=finding.operator, summary=finding.summary,
            clean=clean, mutated=mutated,
        )
        for attempt in range(1, max_attempts + 1):
            code = _python(model.ask("remediate", prompt))
            verdict = tools.propose_closing_test(finding.operator, code)
            finding.attempts = attempt
            finding.gate = verdict.reason
            if verdict.accepted:
                finding.closing_test = code
                finding.closing_test_failure = verdict.failure_line
                log(f"    closes {finding.operator} (attempt {attempt})")
                break
            log(f"    attempt {attempt} rejected: {verdict.reason}")
            prompt = REVISE_CLOSING_TEST.format(
                instructions=INSTRUCTIONS, code=code, verdict=verdict.reason,
                output=verdict.output[-1200:], operator=finding.operator,
                clean=clean, mutated=mutated,
            )

    trajectory.event("report", "findings", survivors=result.survivors,
                     closed=[f.operator for f in result.findings if f.closed],
                     kill_rate_before=round(result.kill_rate_before, 4))
    return result


# ---------------------------------------------------------------------------
# Reading a small model's answers
# ---------------------------------------------------------------------------

def _parse_prior(raw: str, valid: set[str]) -> dict:
    """The Prior is evidence, not input to a decision, so a garbled one is survivable."""
    prior = {"order": [], "expect_missed": [], "why": "", "invented_ids": []}
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return prior
    try:
        doc = json.loads(match.group(0))
    except json.JSONDecodeError:
        return prior
    listed = [x for x in doc.get("order", []) if isinstance(x, str)]
    missed = [x for x in doc.get("expect_missed", []) if isinstance(x, str)]
    prior["order"] = [x for x in listed if x in valid]
    prior["expect_missed"] = [x for x in missed if x in valid]
    prior["invented_ids"] = sorted({x for x in listed + missed if x not in valid})
    prior["why"] = str(doc.get("why", ""))[:400]
    return prior


def _order(operators: list, order: list[str]) -> list:
    by_id = {op.id: op for op in operators}
    ranked = [by_id[i] for i in order if i in by_id]
    return ranked + [op for op in operators if op not in ranked]


def _python(raw: str) -> str:
    """Pull runnable Python out of whatever the model actually said.

    An 8B model wraps code in fences, prefaces it with a sentence, or appends an
    explanation. None of that is a reason to spend a Gate run, so it is stripped
    here — and if what is left will not compile, trailing lines come off until it
    does, which is the common shape of the failure.
    """
    fenced = re.findall(r"```(?:python)?\s*\n(.*?)```", raw, re.S)
    code = fenced[0] if fenced else raw
    lines = code.splitlines()
    start = next(
        (i for i, l in enumerate(lines)
         if l.startswith(("import ", "from ", "def ", "@", "#"))),
        0,
    )
    lines = lines[start:]
    while lines:
        candidate = "\n".join(lines).strip() + "\n"
        try:
            compile(candidate, "<closing test>", "exec")
            return candidate
        except SyntaxError:
            lines.pop()
    return code.strip() + "\n"
