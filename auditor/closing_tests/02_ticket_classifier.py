"""Closing Tests the Auditor wrote for 02_ticket_classifier.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-02_ticket_classifier.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: classify.collapse — Every input is classified into the single most common label.
# gate: green on the clean feature, red under classify.collapse, green under model.swap, model.pin_previous
# fails as: FAILED tests/test_greenwash_closing.py::test_label_for_t2 - AssertionError: a...
import json
import re
from feature import classify

def test_label_for_t2():
    result = classify("t2")
    assert result["label"] == "technical"
