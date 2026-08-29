# Trust Report — 02_ticket_classifier

**The feature.** Routes support tickets to a queue, with an LLM judge in the test suite scoring each answer.

**The suite.** Looks rigorous — an LLM judge, several cases, a confidence floor. The judge prompt asks whether the label is 'reasonable'.

**Kill rate: 50%** — 2 of 4 sabotages were noticed.

2 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

1 of them now has a test that would have caught it.

## `classify.confidence_pin`

Confidence is pinned high regardless of how uncertain the model was.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: false alarm: the feature still works under model.swap and the test went red anyway

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. false alarm: the feature still works under model.swap and the test went red anyway
2. false alarm: the feature still works under model.swap and the test went red anyway
3. false alarm: the feature still works under model.swap and the test went red anyway

## `classify.collapse`

Every input is classified into the single most common label.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under classify.collapse, green under model.swap, model.pin_previous
- it fails as: `FAILED tests/test_greenwash_closing.py::test_label_for_t2 - AssertionError: a...`
- attempts needed: 2

```python
import json
import re
from feature import classify

def test_label_for_t2():
    result = classify("t2")
    assert result["label"] == "technical"
```

Rejected by the gate along the way:

1. classify.collapse was applied and the test still passed

## What the auditor expected, before it ran anything

Predicted misses: `classify.confidence_pin`

Actually missed: `classify.confidence_pin`, `classify.collapse`

> The suite checks for reasonable routing but doesn't validate confidence levels, so confidence pinning would go undetected.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
