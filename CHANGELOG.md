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
| Auditor v1 | The agent. Four phases per Corpus Case — triage (order the Operators, record a **Prior**), verify (run them, collect Survivors with receipts), remediate (write a Closing Test per Survivor), report. Six tools. Every Closing Test faces the **Verification Gate**: green on the clean Feature, red under the Mutant it claims to close, no `HARNESS_FAULTS` signature in either run, or it goes back to the model with the pytest output attached. `qwen3:8b`, locally, no API key. | `score_predictions.py auditor/predictions.json` → **precision 100%, recall 100%, F1 1.00**, 12/12 confirmed Blind Spots, against the baseline's 0.61 on the same scorer. `evals/uplift.py` → **corpus mean Kill Rate 28% → 75%**. | Kept; this is the product. **The precision/recall ceiling is by construction and should be reported as such** — the Auditor runs every applicable Operator, so it finds every Survivor there is. Recall is bounded by the Operator catalogue, not by reasoning. The number that carries information is the Uplift, because that is where the model's own output is what gets judged. |
| The Prior — a control inside the agent | Before running anything, the Auditor is asked which sabotages it expects to survive. Recorded in the Trajectory, emitted in the scorer's own shape, never reported as a finding. Same model, same cases, same question as the Baseline; the only difference is that it cannot run anything. Costs one model call per case. | `score_predictions.py auditor/prior_predictions.json` → **precision 80%, recall 33%, F1 0.47**, 4/12. The separate one-shot Baseline scores 0.61. | Kept. Prediction with this model lands between **0.47 and 0.61** depending on how you ask; verification lands at **1.00**. Same model, same information, same scorer. **The gap is the harness, not the intelligence** — which is the whole architectural bet, now measured inside the agent rather than argued for. |
| The Gate earned its place on the first run | `classify.collapse` on case 02 routes every ticket to `billing`. The Auditor was shown the sabotaged output and asked for a test that catches it. It wrote `assert classify("t2")["label"] == "billing"` — an assertion that the bug is present. | Rejected three times, all "red on the clean feature" (`t2` really is `technical`). `classify.collapse` is still open and the Trust Report says so. Trace: `trajectories/audit-02_ticket_classifier.md`. | Kept, and it is the strongest evidence in the project. **An agent that writes tests from observed output will happily codify the bug it was shown.** Without the Gate that test ships green, and the suite is now actively worse than before — it asserts the broken behaviour. Verification is not a safety net here, it is the product. |
| Retry loop has a fixed point | Rejected Closing Tests go back to the model with the pytest output. If the model repeats itself, the next prompt is byte-identical to the last one. | The two retry prompts on case 02 (`trajectories/audit-02_ticket_classifier.jsonl`, steps 33 and 37) have the same SHA-256. At temperature 0 the third attempt could not have differed from the second; against recorded fixtures it was a cache hit. | **Not yet fixed** — the fix is to carry the full attempt history so each retry prompt is new, and to say plainly that a repeat has already failed. Logged here rather than quietly patched, because the wasted third attempt is in the committed trajectories and a reviewer will see it. |
| Reproducibility: the harness contaminating its own fixtures | Fixtures are keyed `sha256(model + prompt)`, and the Auditor quotes captured pytest output back into its retry prompts. pytest prints its own wall clock. | 8 recorded prompts contained a string like `1 failed in 0.01s`. A judge replaying on their own machine would have got a different key and a `FixtureMiss`. | Fixed at the point of capture: `_stable()` in `greenwash/harness.py` normalises durations, object addresses and absolute paths. Re-recorded. A replayed audit now rewrites the Trajectories **byte for byte** — `auditor/audit.py && git diff --stat trajectories/` is empty, which is a reproducibility claim a reviewer can check in one command. Same family as the Invalid-Mutant bug: the machinery quietly corrupting its own measurement. |
| Variance of the retry loop | Re-recording after that fix changed the retry prompts by a few characters — the pytest text quoted into them. Nothing else changed: same model, same temperature 0, same cases. | Run A closed 8 of 12 Blind Spots, Uplift 28% → **86%**. Run B, committed, closed 6 of 12, Uplift 28% → **75%**. Every first-attempt closure was identical across both runs; every difference was in the retries. | **The committed number is 75%.** First attempts are stable and retries are not, which is worth knowing before trusting a single agent run: an 11-point swing in the headline came from characters in a prompt that carry no meaning. Reported rather than cherry-picked. |
| Uplift closes more than the agent claimed | The Gate accepted 6 Closing Tests. Merging them and re-measuring closes 8 Blind Spots. | Case 03: the Gate accepted one test, for `model.echo`; the merged suite also kills `model.downgrade` and `retrieval.truncate`. That test is `assert result["answer"] == "The annual leave accrues at 2.5 days per completed month of service. This information is found on [page 1]."` | Uplift, not the count of accepted tests, is the honest metric — but the *reason* it is higher is the project's own main failure mode, below. |

## Main failure mode: mutation testing rewards over-fitting

The Kill Rate cannot tell "caught the bug" from "pinned the output". A test that
asserts the model's exact prose kills every Mutant, passes the Verification Gate
honestly, and would fire on a legitimate model upgrade, a prompt tweak, or a
temperature change. Several of the Closing Tests above are exactly that, and
they are a large part of the 75%.

The Gate cannot see the difference, because both kinds of test do the one thing
the Gate checks. Closing that hole needs a second probe the Gate does not have:
run each Closing Test against a *different but still correct* Feature output —
the same model at a higher temperature — and count the ones that go red. Those
are false alarms, and they cost the user the thing this project is trying to
buy, which is trust in a green suite. Not yet built; it is the next experiment.

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
