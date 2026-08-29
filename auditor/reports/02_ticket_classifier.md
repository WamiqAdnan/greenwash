# Trust Report — 02_ticket_classifier

**The feature.** Routes support tickets to a queue, with an LLM judge in the test suite scoring each answer.

**The suite.** Looks rigorous — an LLM judge, several cases, a confidence floor. The judge prompt asks whether the label is 'reasonable'.

**Kill rate: 50%** — 2 of 4 sabotages were noticed.

2 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

2 of them now have a test that would have caught it.

## `classify.confidence_pin`

Confidence is pinned high regardless of how uncertain the model was.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under classify.confidence_pin, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_confidence_pin_bypassed - assert...`
- attempts needed: 1

```python
import json
import re
from feature import classify

def test_confidence_pin_bypassed():
    assert classify("t1")["confidence"] == 0.95
    assert classify("t2")["confidence"] == 0.95
    assert classify("t3")["confidence"] == 0.95
```

## `classify.collapse`

Every input is classified into the single most common label.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under classify.collapse, no benign change is measurable on this feature
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
