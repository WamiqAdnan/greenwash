# Greenwash

A tool that breaks the code an eval suite guards, to find out whether the suite
would notice. A green suite is a claim; a **Kill Rate** is evidence.

Built for the micro1 Agentic Workflows Hackathon, 28–31 August 2026.

## Language

### The thing being judged

**Corpus Case**:
One small AI feature, its own test suite, and the **Blind Spots** we deliberately
built into that suite. Twelve of these are the evaluation set. A case owns its
`feature.py`, `tests/`, `fixtures/`, `case.json` and `blindspots.json`.
_Avoid_: repo, project, sample

**Suite**:
The tests a Corpus Case shipped with, run unchanged. Greenwash never edits a
suite to make a point — it runs the tests the team actually wrote.
_Avoid_: test file, spec

**Feature**:
The AI-backed function a Suite is supposed to guard. Always exposes its work
through module-level names (`extract`, `classify`, `answer`, `retrieve`) so an
**Operator** can replace one.
_Avoid_: system under test, SUT, app

### The sabotage

**Operator**:
One named, reversible way an AI feature breaks quietly — the model gets swapped
for a weaker one, every amount comes back zero, a citation points one page off.
Carries `tags`; only Operators whose tags a Corpus Case declares are applied to it.
_Avoid_: mutation type, rule, check

**Mutant**:
A Corpus Case with exactly one Operator applied. Every Mutant runs in a fresh
subprocess, because a patch that leaks between Mutants corrupts every later result.
_Avoid_: variant, run

**Killed**:
The Suite went red under a Mutant. The suite noticed. Good.
_Avoid_: caught, detected, passed

**Survivor**:
The Suite stayed green under a Mutant. The suite is blind to that failure, and the
Mutant is the receipt. Every finding Greenwash reports is a Survivor.
_Avoid_: miss, gap, escape

**Invalid**:
The Suite went red because *Greenwash* broke — a missing fixture, an unknown
Operator. Indistinguishable from a Kill unless you look, which is why
`HARNESS_FAULTS` exists. Invalid Mutants are excluded from the Kill Rate and
reported loudly. **An Invalid Mutant counted as a Kill silently inflates the
headline number** — this bug was real, see the Changelog.
_Avoid_: error, skipped

### The agent

**Auditor**:
The agent that reads a Corpus Case, runs Operators against it, and writes the
tests that close what survived. It **never predicts** which sabotages survive —
it runs them and observes. Every finding it reports is a Survivor with a run
attached. Contrast the **Baseline**, which is only allowed to predict.
_Avoid_: analyser, scanner, reviewer

**Baseline**:
One model call per Corpus Case, given the Feature, the Suite and the whole
Operator catalogue, asked which sabotages the Suite would miss. It cannot run
anything. Prediction versus verification is the only variable between it and the
Auditor, and both are scored by `evals/score_predictions.py`.
_Avoid_: control, naive version

**Prior**:
What the Auditor expected before it ran anything, recorded in its Trajectory.
Kept as evidence and never reported as a finding — a Prior that turns out wrong
is the point of the project, not a bug.
_Avoid_: guess, hypothesis

**Closing Test**:
A test the Auditor wrote that turns a Survivor into a Killed. Added to a Suite,
never edited into one — Closing Tests live in `auditor/closing_tests/` and are
merged onto an **Overlay** to be measured.
_Avoid_: fix, patch, new test

**Verification Gate**:
The two runs every Closing Test must survive before the Auditor is allowed to
report it: green on the clean Feature, red under the Mutant it claims to close,
and neither run tripping a `HARNESS_FAULTS` signature. A Closing Test that fails
the Gate goes back to the Auditor with the pytest output attached. **This is
where a local model's bad assertions die** rather than reaching the user.
_Avoid_: validation, check

**Overlay**:
A scratch copy of a Corpus Case with Closing Tests dropped into its `tests/`.
The way Uplift is measured without ever editing a Suite, which is evidence.
_Avoid_: patched case, fork

**Uplift**:
Kill Rate before Closing Tests and after, on the same Corpus Case. The number
the intended user actually cares about — Kill Rate says how blind the Suite is,
Uplift says how much of that the Auditor closed. Measured by `evals/uplift.py`,
outside the agent, so the agent never scores itself.
_Avoid_: improvement, delta, gain

### The measurement

**Kill Rate**:
Killed Mutants over *valid* Mutants. The number in the **Trust Report** and the
number the Improvement Changelog moves. Never computed over Invalid Mutants.
_Avoid_: score, coverage, pass rate

**Blind Spot**:
A Survivor that a human has confirmed is genuinely a hole in the Suite rather
than an artifact of our own machinery. `blindspots.json` records the confirmed
set per Corpus Case; the eval reports any drift between measured and confirmed.
_Avoid_: bug, issue, gap

**Trust Report**:
What the intended user reads: the Survivors, the Kill Rate before and after, and
the tests that would have closed each hole. The deliverable, not a log.
_Avoid_: output, results, findings

### The runtime

**Fixture**:
One recorded model answer, keyed by model and prompt. Replay is not a testing
convenience — it is what makes a Kill Rate a fact rather than a sample. A Survivor
under replay survived because the Suite is blind, never because the model
answered differently that time.
_Avoid_: cassette, mock, stub

**Record Plan**:
A Corpus Case's list of every model call its Suite will make, so recording covers
replay completely. Operators that change the prompt (anything under `retrieval.`)
get their own recording pass.
_Avoid_: manifest, script

**Selftest**:
One of Greenwash's own tests, under `selftests/`. Deliberately not called a
Suite: that word belongs to a Corpus Case's own tests, and blurring the two is
how you end up editing evidence.
_Avoid_: unit test, our tests

**Weak Model**:
The deliberately worse model `model.downgrade` swaps in — `qwen3:0.6b` against a
`qwen3:8b` baseline. Real, not simulated: it has its own recorded Fixtures, and
the degradation it causes is one you can read.
_Avoid_: bad model, dummy
