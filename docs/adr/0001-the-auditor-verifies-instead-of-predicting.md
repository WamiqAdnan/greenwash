# 0001 — The Auditor verifies instead of predicting

**Status** accepted, 29 Aug 2026
**Supersedes** an earlier note in `STATE.md` that said the auditor needs
reasoning `qwen3:8b` does not have.

## Context

Greenwash has two jobs that look like one job.

**Predict** which sabotages a Suite would miss, by reading the Feature and the
Suite. This is hard. The Baseline does exactly this, deliberately well fed — it
gets the Feature, the Suite and the whole Operator catalogue — and it scored
precision 64% / recall 58% / F1 0.61 on `qwen3:8b`. The shape of its errors is
worse than the score: on `01_invoice_extractor` it got five of six Operators
backwards, flagging the two the Suite actually catches (`model.echo`,
`schema.drop_field` — both crash) and missing all three value corruptions, which
are the entire point of a Suite that checks key presence and never a value. It
reasoned about loud failures and was blind to silent ones. That is the failure
this project exists to fix, reproduced in the thing measuring it.

**Find** which sabotages a Suite misses, by applying each one and running the
Suite. This is not hard. It is a subprocess and an exit code.

An earlier decision conflated the two and concluded the auditor needed a
frontier model. It does not, because the auditor is not doing the first job.

## Decision

The Auditor never predicts. It applies each Operator, runs the Suite, and reads
the result. `qwen3:8b`, locally, is enough — which also means a judge reproduces
the entire pipeline, agent included, with no API key.

The model is left with the one task that genuinely needs a model: given a
Survivor and the values the Feature actually returned before and after the
sabotage, write the assertion that would have caught it.

And it is not trusted there either. Every Closing Test faces the **Verification
Gate** — green on the clean Feature, red under the Mutant it claims to close,
neither run tripping a `HARNESS_FAULTS` signature — or it goes back to the model
with the pytest output attached. A small model's bad assertion dies in the Gate
instead of reaching the user.

We also keep the model's **Prior**: before anything runs, it is asked which
sabotages it expects to survive. The Prior is recorded in the Trajectory as
evidence and never reported as a finding. It costs one model call and it turns
every audit into a fresh replication of the Baseline experiment.

## Consequences

- Precision and recall against the confirmed Blind Spots are near-ceiling by
  construction, and that number is only interesting next to the Baseline's 0.61
  on the same scorer. Recall is bounded by the Operator catalogue, not by
  reasoning: a failure mode with no Operator is invisible no matter how good the
  model is. **Say this out loud rather than claiming the ceiling as a win.**
- The interesting metric moves to **Uplift** — Kill Rate before and after the
  Closing Tests are merged — where the model's actual output is what is being
  judged, and where a local model can and does fall short.
- The Gate makes the Auditor's cost mostly subprocesses rather than tokens: one
  model call per Survivor when it gets the test right first time, plus one per
  rejected attempt.
- A structured four-phase loop was chosen over a free-form ReAct loop. At 8B,
  a free-form loop spends its budget deciding what to do next; the reliability
  here comes from the Gate and the Harness, and phases put the tokens where the
  model is actually useful. The retry loop inside remediation is where the agent
  genuinely reacts to an observation.
