# Trust Report — 05_meeting_summariser

**The feature.** Summarises a meeting transcript into a paragraph covering decisions, owners and dates.

**The suite.** Checks a summary came back, that it is shorter than the transcript, and that it is not a stub. Never checks that anything the meeting decided is in it.

**Kill rate: 0%** — 0 of 4 sabotages were noticed.

4 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

1 of them now has a test that would have caught it.

## `model.echo`

The model is replaced by one that echoes its input back.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under model.echo, green under prompt.reword
- it fails as: `FAILED tests/test_greenwash_closing.py::test_summary_contains_key_decisions`
- attempts needed: 1

```python
from feature import read_transcript, summarise

def test_summary_contains_key_decisions():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "exponential backoff" in standup and "Kafka upgrade" in standup
    assert "starter tier price" in pricing and "discount experiment" in pricing
```

## `summary.drop_decisions`

Everything the meeting decided is dropped; the discussion is kept.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: summary.drop_decisions was applied and the test still passed

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. summary.drop_decisions was applied and the test still passed
2. summary.drop_decisions was applied and the test still passed
3. summary.drop_decisions was applied and the test still passed

## `model.downgrade`

The model behind the feature is swapped for a much weaker one.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. false alarm: the feature still works under prompt.reword and the test went red anyway
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `summary.extractive`

The summary is the transcript's own opening lines rather than a summary.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. false alarm: the feature still works under prompt.reword and the test went red anyway
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## What the auditor expected, before it ran anything

Predicted misses: `summary.drop_decisions`, `summary.extractive`

Actually missed: `model.echo`, `summary.drop_decisions`, `model.downgrade`, `summary.extractive`

> The suite only checks for non-empty output, length, and existence, which are not affected by echo or model downgrade, but are bypassed by summary changes that still meet the criteria.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
