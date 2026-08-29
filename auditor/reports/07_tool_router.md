# Trust Report — 07_tool_router

**The feature.** Chooses the tool that handles a support request and fills in its arguments.

**The suite.** Checks the right tool fired and that arguments is a dict. Never checks a single argument value, which is the half that moves money.

**Kill rate: 50%** — 2 of 4 sabotages were noticed.

2 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

1 of them now has a test that would have caught it.

## `tool.swap_args`

Two argument values are swapped — the refund goes to the wrong account.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. false alarm: the feature still works under model.swap and the test went red anyway
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `tool.blank_args`

The right tool is called with empty arguments.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under tool.blank_args, green under model.swap, model.pin_previous
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
