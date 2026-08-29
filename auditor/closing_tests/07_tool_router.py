"""Closing Tests the Auditor wrote for 07_tool_router.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-07_tool_router.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: tool.blank_args — The right tool is called with empty arguments.
# gate: green on the clean feature, red under tool.blank_args, green under model.swap, model.pin_previous
# fails as: FAILED tests/test_greenwash_closing.py::test_arguments_are_non_empty - Assert...
from feature import route

def test_arguments_are_non_empty():
    assert route("r1")["arguments"]["amount"] != ""
    assert route("r1")["arguments"]["order_id"] != ""
    assert route("r2")["arguments"]["customer_id"] != ""
    assert route("r2")["arguments"]["new_address"] != ""
    assert route("r3")["arguments"]["reason"] != ""
