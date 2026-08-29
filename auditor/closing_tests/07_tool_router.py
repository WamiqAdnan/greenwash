"""Closing Tests the Auditor wrote for 07_tool_router.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-07_tool_router.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: tool.swap_args — Two argument values are swapped — the refund goes to the wrong account.
# gate: green on the clean feature, red under tool.swap_args, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}


# closes: tool.blank_args — The right tool is called with empty arguments.
# gate: green on the clean feature, red under tool.blank_args, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_arguments_are_non_empty - Assert...
from feature import route

def test_arguments_are_non_empty():
    assert route("r1")["arguments"]["amount"] != ""
    assert route("r1")["arguments"]["order_id"] != ""
    assert route("r2")["arguments"]["customer_id"] != ""
    assert route("r2")["arguments"]["new_address"] != ""
    assert route("r3")["arguments"]["reason"] != ""
