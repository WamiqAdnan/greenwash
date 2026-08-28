"""Closing Tests the Auditor wrote for 02_ticket_classifier.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it. Written by `auditor/audit.py`; the
reasoning and the rejected attempts are in
`trajectories/audit-02_ticket_classifier.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: classify.confidence_pin — Confidence is pinned high regardless of how uncertain the model was.
# gate: green on the clean feature, red under classify.confidence_pin
# fails as: FAILED tests/test_greenwash_closing.py::test_confidence_pin_bypassed - assert...
import json
import re
from feature import classify

def test_confidence_pin_bypassed():
    assert classify("t1")["confidence"] == 0.95
    assert classify("t2")["confidence"] == 0.95
    assert classify("t3")["confidence"] == 0.95


# closes: classify.collapse — Every input is classified into the single most common label.
# gate: green on the clean feature, red under classify.collapse
# fails as: FAILED tests/test_greenwash_closing.py::test_label_for_t2 - AssertionError: a...
import json
import re
from feature import classify

def test_label_for_t2():
    result = classify("t2")
    assert result["label"] == "technical"
