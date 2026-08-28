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
| Baseline (prediction) | One prompt per case, no tools. Given the feature, the suite, and the **full Operator catalogue**, asked which sabotages the suite would miss. Deliberately well-fed: the only thing it cannot do is run anything, so the variable under test is prediction versus verification and nothing else. Model qwen3:8b, 15s for the corpus. | **precision 64%, recall 58%, F1 0.61** — found 7 of 12 confirmed Blind Spots | Kept as the baseline. The shape of the errors matters more than the score: on case 01 it got 5 of 6 Operators **backwards**. It flagged `model.echo` and `schema.drop_field` — both of which the suite actually catches, because both crash — and missed all three value corruptions, which are the whole point of a suite that checks key presence and never a value. It reasoned about loud failures and was blind to silent ones. That is the same failure this project exists to fix, reproduced in the baseline. |

## Caveat on the baseline number

The 64/58/0.61 above is a **qwen3:8b baseline**, because no frontier API key was
configured when it was run. A frontier model will almost certainly score higher,
and the honest headline comparison requires running the baseline and the agent
on the *same* model. Treat 0.61 as a provisional floor, not the number to quote.
`baseline/predict.py` takes `--model`; re-run it before the submission and
update this row.

## Not yet run

- **The auditor agent itself.** Everything above is the measurement rig. The
  agent that *finds* Blind Spots and *writes* the closing tests does not exist yet.
- **Local-auditor experiment.** Drive the auditor with qwen3:8b and measure
  against a frontier model. Prediction, recorded before the run: the local model
  proposes sabotages that crash rather than sabotages that are silently wrong,
  so its Mutants get trivially Killed and suites look healthier than they are.
  Evidence for the prediction is in this session's benchmark — asked to name
  ways code could break *silently*, qwen3:8b described crashes.
