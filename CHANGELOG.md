# Improvement Changelog

Required deliverable. One entry per meaningful experiment, written when it was
run, with the evidence that drove the next decision. Experiments that were
removed stay in this file — what they taught us is the point.

Measurement is always `python evals/run_eval.py`, corpus mean Kill Rate.

| Stage | What was tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Scaffold | Harness that runs each Corpus Case's own suite once per Operator, in a fresh subprocess. First Operator library: 12 sabotages tagged by capability. | Case 01 ran 6 Mutants, 50% Kill Rate | Kept. The loop works and the number moves. |
| Integrity fix | `model.downgrade` reported as Killed on case 01. Checked by hand rather than believing it. It was a **fixture miss**: the weak model had no recordings, the suite errored, and the harness scored the crash as a detection. | Case 01 Kill Rate 50% → **33%** once the false Kill was removed | Kept, and it changed the design. Added `HARNESS_FAULTS` and an Invalid state so a harness fault can never again be counted as a Kill. **A tool that measures test quality is worthless if it cannot tell its own failure from a detection** — this is the failure mode to watch for the rest of the build. |
| Fixture coverage | Retrieval Operators rewrite the context the model sees, so case 03's `retrieval.*` Mutants died of fixture misses and reported Invalid. | 2 of 6 Mutants unusable on case 03 | Kept. `record_fixtures.py` now does an extra recording pass per prompt-changing Operator. All 16 Mutants across 3 cases now valid. |
| Baseline (corpus) | Three Corpus Cases, hand-confirmed Blind Spots, all Mutants valid. | **corpus mean Kill Rate 28%** — case 01 33%, case 02 50%, case 03 **0%** | This is the number to beat. Case 03 kills nothing at all: a suite that checks citations exist but never that they are true is blind to every sabotage including replacing the model with one that echoes its input. |

## Not yet run

- **Baseline comparison.** One direct prompt — "here is my suite and the code it
  tests, what is missing?" — scored on the same corpus with the same
  blind-spot recall metric. Required before any improvement claim means anything.
- **The auditor agent itself.** Everything above is the measurement rig. The
  agent that *finds* Blind Spots and *writes* the closing tests does not exist yet.
- **Local-auditor experiment.** Drive the auditor with qwen3:8b and measure
  against a frontier model. Prediction, recorded before the run: the local model
  proposes sabotages that crash rather than sabotages that are silently wrong,
  so its Mutants get trivially Killed and suites look healthier than they are.
  Evidence for the prediction is in this session's benchmark — asked to name
  ways code could break *silently*, qwen3:8b described crashes.
