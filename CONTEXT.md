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

**Weak Model**:
The deliberately worse model `model.downgrade` swaps in — `qwen3:0.6b` against a
`qwen3:8b` baseline. Real, not simulated: it has its own recorded Fixtures, and
the degradation it causes is one you can read.
_Avoid_: bad model, dummy
