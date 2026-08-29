# Trust Report — 07_tool_router

**The feature.** Chooses the tool that handles a support request and fills in its arguments.

**The suite.** Checks the right tool fired and that arguments is a dict. Never checks a single argument value, which is the half that moves money.

**Kill rate: 50%** — 2 of 4 sabotages were noticed.

2 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

2 of them now have a test that would have caught it.

## `tool.swap_args`

Two argument values are swapped — the refund goes to the wrong account.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under tool.swap_args, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct`
- attempts needed: 1

```python
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
```

## `tool.blank_args`

The right tool is called with empty arguments.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under tool.blank_args, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_arguments_are_non_empty - Assert...`
- attempts needed: 1

```python
from feature import route

def test_arguments_are_non_empty():
    assert route("r1")["arguments"]["amount"] != ""
    assert route("r1")["arguments"]["order_id"] != ""
    assert route("r2")["arguments"]["customer_id"] != ""
    assert route("r2")["arguments"]["new_address"] != ""
    assert route("r3")["arguments"]["reason"] != ""
```

## What the auditor expected, before it ran anything

Predicted misses: `tool.swap_args`

Actually missed: `tool.swap_args`, `tool.blank_args`

> The suite only checks for the correct tool being chosen, not the correctness of the arguments, so it will miss argument swaps.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
