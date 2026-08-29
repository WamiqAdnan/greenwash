# Trust Report — 10_few_shot_leak

**The feature.** Routes tickets using an internal convention taught to the model by five few-shot examples.

**The suite.** Exact-label assertions on five cases. Rigorous by every measure Greenwash has — and the five cases are the five examples in the prompt.

**Kill rate: 100%** — 2 of 2 sabotages were noticed.

No sabotage survived this suite.

## Tried, and nothing happened

These sabotages were applied and your feature returned exactly what it returned before. Your suite stayed green because there was nothing to notice — this is not a hole:

- `model.downgrade`

## What the auditor expected, before it ran anything

Predicted misses: `classify.collapse`

Actually missed: (none)

> The suite explicitly tests all labels and expected outcomes, making it most likely to catch echo and downgrade, but collapse is a structural change that the suite does not test.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
