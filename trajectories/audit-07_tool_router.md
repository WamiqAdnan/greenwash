# Trajectory — auditor-v1 on 07_tool_router

- model: `qwen3:8b` (replay mode)
- tools: `read_feature`, `read_suite`, `list_operators`, `observe`, `run_operator`, `propose_closing_test`
- closing-test attempts allowed per survivor: 3
- operator budget: none (whole applicable catalogue)

## The agent's instructions

```
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.
```


## Phase 1 — triage: read the case, order the sabotages, record a prior

**2. tool call** `read_feature(case='07_tool_router')`

**3. read_feature responded**

```
"""Tool routing — the feature under test.

Picks the tool for a support request and fills in its arguments. The arguments
are the part that moves money.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

TOOLS = [
    {"name": "issue_refund", "arguments": ["order_id", "amount"]},
    {"name": "update_address", "arguments": ["customer_id", "new_address"]},
    {"name": "escalate_to_human", "arguments": ["reason"]},
]

REQUESTS = {
    "r1": "Order A-4471 was charged 84.00 twice. Refund the duplicate.",
    "r2": "Customer 90210 has moved to 14 Marina Walk, Dubai. Update their address.",
    "r3": "I want to speak to a manager about my last three deliveries.",
}

PROMPT = """Choose exactly one tool for the request and fill in its arguments.

Tools:
{tools}

Reply with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Pick the single tool that handles the request below and
supply its arguments.

Tools:
{tools}

Respond with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def route(request_id: str) -> dict:
    """Return the tool call for one of the known requests."""
    raw = complete(PROMPT.format(tools=_catalogue(), request=REQUESTS[request_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    call = json.loads(match.group(0))
    call.setdefault("arguments", {})
    return call
```

**4. tool call** `read_suite(case='07_tool_router')`

**5. read_suite responded**

```
"""The suite that grew up alongside the router.

It checks the right tool fires, which is what went wrong in early testing and
what everyone therefore wrote tests for. The arguments were always right, so
nobody wrote a test for them.
"""

from feature import TOOLS, route

EXPECTED_TOOL = {
    "r1": "issue_refund",
    "r2": "update_address",
    "r3": "escalate_to_human",
}


def test_the_right_tool_is_chosen():
    for request_id, tool in EXPECTED_TOOL.items():
        assert route(request_id)["tool"] == tool


def test_the_tool_is_one_that_exists():
    names = {t["name"] for t in TOOLS}
    for request_id in EXPECTED_TOOL:
        assert route(request_id)["tool"] in names


def test_arguments_are_supplied():
    for request_id in EXPECTED_TOOL:
        assert isinstance(route(request_id)["arguments"], dict)
```

**6. tool call** `list_operators(tags=['llm', 'tool_use'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `tool.blank_args` — The right tool is called with empty arguments.
- `tool.swap_args` — Two argument values are swapped — the refund goes to the wrong account.
```

**8. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Tool routing — the feature under test.

Picks the tool for a support request and fills in its arguments. The arguments
are the part that moves money.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

TOOLS = [
    {"name": "issue_refund", "arguments": ["order_id", "amount"]},
    {"name": "update_address", "arguments": ["customer_id", "new_address"]},
    {"name": "escalate_to_human", "arguments": ["reason"]},
]

REQUESTS = {
    "r1": "Order A-4471 was charged 84.00 twice. Refund the duplicate.",
    "r2": "Customer 90210 has moved to 14 Marina Walk, Dubai. Update their address.",
    "r3": "I want to speak to a manager about my last three deliveries.",
}

PROMPT = """Choose exactly one tool for the request and fill in its arguments.

Tools:
{tools}

Reply with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Pick the single tool that handles the request below and
supply its arguments.

Tools:
{tools}

Respond with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def route(request_id: str) -> dict:
    """Return the tool call for one of the known requests."""
    raw = complete(PROMPT.format(tools=_catalogue(), request=REQUESTS[request_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    call = json.loads(match.group(0))
    call.setdefault("arguments", {})
    return call

```

## The suite that guards it

```python
"""The suite that grew up alongside the router.

It checks the right tool fires, which is what went wrong in early testing and
what everyone therefore wrote tests for. The arguments were always right, so
nobody wrote a test for them.
"""

from feature import TOOLS, route

EXPECTED_TOOL = {
    "r1": "issue_refund",
    "r2": "update_address",
    "r3": "escalate_to_human",
}


def test_the_right_tool_is_chosen():
    for request_id, tool in EXPECTED_TOOL.items():
        assert route(request_id)["tool"] == tool


def test_the_tool_is_one_that_exists():
    names = {t["name"] for t in TOOLS}
    for request_id in EXPECTED_TOOL:
        assert route(request_id)["tool"] in names


def test_arguments_are_supplied():
    for request_id in EXPECTED_TOOL:
        assert isinstance(route(request_id)["arguments"], dict)

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `tool.blank_args` — The right tool is called with empty arguments.
- `tool.swap_args` — Two argument values are swapped — the refund goes to the wrong account.

## Your task

Order the sabotages, most likely to slip past this suite first. Then say which
you expect it to miss. You will find out; this is recorded so we can compare
what you expected with what actually happened.

Reply with JSON only:

{"order": ["sabotage.id", ...], "expect_missed": ["sabotage.id", ...], "why": "one sentence"}

JSON:
````

</details>

**9. `qwen3:8b` answered**

```
{"order": ["tool.swap_args", "model.downgrade", "tool.blank_args", "model.echo"], "expect_missed": ["tool.swap_args"], "why": "The suite only checks for the correct tool being chosen, not the correctness of the arguments, so it will miss argument swaps."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "tool.swap_args",
    "model.downgrade",
    "tool.blank_args",
    "model.echo"
  ],
  "expect_missed": [
    "tool.swap_args"
  ],
  "why": "The suite only checks for the correct tool being chosen, not the correctness of the arguments, so it will miss argument swaps.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='tool.swap_args')`

**12. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**13. tool call** `run_operator(operator='model.downgrade')`

**14. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_right_tool_is_chosen - AssertionError:...
is_one_that_exists():
        names = {t["name"] for t in TOOLS}
        for request_id in EXPECTED_TOOL:
>           assert route(request_id)["tool"] in names
E           AssertionError: assert 'issue_refund(order_id, amount)' in {'escalate_to_human', 'issue_refund', 'update_address'}

tests/test_feature.py:25: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_right_tool_is_chosen - AssertionError:...
FAILED tests/test_feature.py::test_the_tool_is_one_that_exists - AssertionErr...
2 failed, 1 passed in N.NNs
```

**15. tool call** `run_operator(operator='tool.blank_args')`

**16. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**17. tool call** `run_operator(operator='model.echo')`

**18. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_right_tool_is_chosen - json.decoder.JS...
ry:
>           obj, end = self.scan_once(s, idx)
                       ^^^^^^^^^^^^^^^^^^^^^^
E           json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 31 (char 30)

.../json/decoder.py:353: JSONDecodeError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_right_tool_is_chosen - json.decoder.JS...
FAILED tests/test_feature.py::test_the_tool_is_one_that_exists - json.decoder...
FAILED tests/test_feature.py::test_arguments_are_supplied - json.decoder.JSON...
3 failed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**19. tool call** `observe(operator=None)`

**20. observe responded**

```
call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": 84.0, "order_id": "A-4471"}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "90210", "new_address": "14 Marina Walk, Dubai"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}
```

**21. tool call** `observe(operator='tool.swap_args')`

**22. observe responded**

```
call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "A-4471", "order_id": 84.0}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "14 Marina Walk, Dubai", "new_address": "90210"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}
```

**23. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Tool routing — the feature under test.

Picks the tool for a support request and fills in its arguments. The arguments
are the part that moves money.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

TOOLS = [
    {"name": "issue_refund", "arguments": ["order_id", "amount"]},
    {"name": "update_address", "arguments": ["customer_id", "new_address"]},
    {"name": "escalate_to_human", "arguments": ["reason"]},
]

REQUESTS = {
    "r1": "Order A-4471 was charged 84.00 twice. Refund the duplicate.",
    "r2": "Customer 90210 has moved to 14 Marina Walk, Dubai. Update their address.",
    "r3": "I want to speak to a manager about my last three deliveries.",
}

PROMPT = """Choose exactly one tool for the request and fill in its arguments.

Tools:
{tools}

Reply with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Pick the single tool that handles the request below and
supply its arguments.

Tools:
{tools}

Respond with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def route(request_id: str) -> dict:
    """Return the tool call for one of the known requests."""
    raw = complete(PROMPT.format(tools=_catalogue(), request=REQUESTS[request_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    call = json.loads(match.group(0))
    call.setdefault("arguments", {})
    return call

```

## The suite that missed this

```python
"""The suite that grew up alongside the router.

It checks the right tool fires, which is what went wrong in early testing and
what everyone therefore wrote tests for. The arguments were always right, so
nobody wrote a test for them.
"""

from feature import TOOLS, route

EXPECTED_TOOL = {
    "r1": "issue_refund",
    "r2": "update_address",
    "r3": "escalate_to_human",
}


def test_the_right_tool_is_chosen():
    for request_id, tool in EXPECTED_TOOL.items():
        assert route(request_id)["tool"] == tool


def test_the_tool_is_one_that_exists():
    names = {t["name"] for t in TOOLS}
    for request_id in EXPECTED_TOOL:
        assert route(request_id)["tool"] in names


def test_arguments_are_supplied():
    for request_id in EXPECTED_TOOL:
        assert isinstance(route(request_id)["arguments"], dict)

```

## What was done to the feature

`tool.swap_args` — Two argument values are swapped — the refund goes to the wrong account.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": 84.0, "order_id": "A-4471"}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "90210", "new_address": "14 Marina Walk, Dubai"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

After `tool.swap_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "A-4471", "order_id": 84.0}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "14 Marina Walk, Dubai", "new_address": "90210"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

## Your task

Write ONE pytest test that FAILS after `tool.swap_args` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**24. `qwen3:8b` answered**

````
```python
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
```
````

**25. tool call** `propose_closing_test(operator='tool.swap_args')`

the test it is asking the gate to judge:

```python
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
```


**26. propose_closing_test responded**

```
rejected: false alarm: the feature still works under model.swap and the test went red anyway
ol"] == "issue_refund"
>       assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
E       AssertionError: assert {'order_id': ...unt': '84.00'} == {'amount': 84...id': 'A-4471'}
E         
E         Omitting 1 identical items, use -vv to show
E         Differing items:
E         {'amount': '84.00'} != {'amount': 84.0}
E         Use -v to get more diff

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```

**27. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## What you have already tried for `tool.swap_args`, and why each one failed

### Attempt 1

```python
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
```

Result: false alarm: the feature still works under model.swap and the test went red anyway

```
def test_issue_refund_arguments_are_correct():
        call = route("r1")
        assert call["tool"] == "issue_refund"
>       assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
E       AssertionError: assert {'order_id': ...unt': '84.00'} == {'amount': 84...id': 'A-4471'}
E         
E         Omitting 1 identical items, use -vv to show
E         Differing items:
E         {'amount': '84.00'} != {'amount': 84.0}
E         Use -v to get more diff

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```


## What the feature actually returns

Before `tool.swap_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": 84.0, "order_id": "A-4471"}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "90210", "new_address": "14 Marina Walk, Dubai"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

After `tool.swap_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "A-4471", "order_id": 84.0}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "14 Marina Walk, Dubai", "new_address": "90210"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

## Your task

Attempt 2. Your last test went red under `model.swap`, which does NOT break the feature — the values it returned were still correct, only worded differently, and your test called that a failure. It is pinned to the exact output this model happened to produce. Assert something that stays true when the wording changes: a fact from the source, a page number, a quote, a number, a structural property — never the model's prose.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`tool.swap_args`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**28. `qwen3:8b` answered**

````
```python
def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"]["amount"] == 84.0
    assert "A-4471" in call["arguments"].values()
```
````

**29. tool call** `propose_closing_test(operator='tool.swap_args')`

the test it is asking the gate to judge:

```python
def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"]["amount"] == 84.0
    assert "A-4471" in call["arguments"].values()
```


**30. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
                                                           [100%]
=================================== FAILURES ===================================
___________________ test_issue_refund_arguments_are_correct ____________________

    def test_issue_refund_arguments_are_correct():
>       call = route("r1")
               ^^^^^
E       NameError: name 'route' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```

**31. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## What you have already tried for `tool.swap_args`, and why each one failed

### Attempt 1

```python
from feature import route

def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
```

Result: false alarm: the feature still works under model.swap and the test went red anyway

```
def test_issue_refund_arguments_are_correct():
        call = route("r1")
        assert call["tool"] == "issue_refund"
>       assert call["arguments"] == {"amount": 84.0, "order_id": "A-4471"}
E       AssertionError: assert {'order_id': ...unt': '84.00'} == {'amount': 84...id': 'A-4471'}
E         
E         Omitting 1 identical items, use -vv to show
E         Differing items:
E         {'amount': '84.00'} != {'amount': 84.0}
E         Use -v to get more diff

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```

### Attempt 2

```python
def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"]["amount"] == 84.0
    assert "A-4471" in call["arguments"].values()
```

Result: red on the clean feature (assertion failed)

```
F                                                                        [100%]
=================================== FAILURES ===================================
___________________ test_issue_refund_arguments_are_correct ____________________

    def test_issue_refund_arguments_are_correct():
>       call = route("r1")
               ^^^^^
E       NameError: name 'route' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```


## What the feature actually returns

Before `tool.swap_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": 84.0, "order_id": "A-4471"}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "90210", "new_address": "14 Marina Walk, Dubai"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

After `tool.swap_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "A-4471", "order_id": 84.0}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "14 Marina Walk, Dubai", "new_address": "90210"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

## Your task

Attempt 3. Your last test failed on the CLEAN feature. Every assertion has to be true of the *before* values above — that is what the feature returns when nothing is wrong.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`tool.swap_args`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**32. `qwen3:8b` answered**

````
```python
def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"]["amount"] == 84.0
    assert call["arguments"]["order_id"] == "A-4471"
```
````

**33. tool call** `propose_closing_test(operator='tool.swap_args')`

the test it is asking the gate to judge:

```python
def test_issue_refund_arguments_are_correct():
    call = route("r1")
    assert call["tool"] == "issue_refund"
    assert call["arguments"]["amount"] == 84.0
    assert call["arguments"]["order_id"] == "A-4471"
```


**34. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
                                                           [100%]
=================================== FAILURES ===================================
___________________ test_issue_refund_arguments_are_correct ____________________

    def test_issue_refund_arguments_are_correct():
>       call = route("r1")
               ^^^^^
E       NameError: name 'route' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_issue_refund_arguments_are_correct
1 failed in N.NNs
```

**35. tool call** `observe(operator='tool.blank_args')`

**36. observe responded**

```
call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "", "order_id": ""}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "", "new_address": ""}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": ""}, "tool": "escalate_to_human"}
```

**37. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Tool routing — the feature under test.

Picks the tool for a support request and fills in its arguments. The arguments
are the part that moves money.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

TOOLS = [
    {"name": "issue_refund", "arguments": ["order_id", "amount"]},
    {"name": "update_address", "arguments": ["customer_id", "new_address"]},
    {"name": "escalate_to_human", "arguments": ["reason"]},
]

REQUESTS = {
    "r1": "Order A-4471 was charged 84.00 twice. Refund the duplicate.",
    "r2": "Customer 90210 has moved to 14 Marina Walk, Dubai. Update their address.",
    "r3": "I want to speak to a manager about my last three deliveries.",
}

PROMPT = """Choose exactly one tool for the request and fill in its arguments.

Tools:
{tools}

Reply with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Pick the single tool that handles the request below and
supply its arguments.

Tools:
{tools}

Respond with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def route(request_id: str) -> dict:
    """Return the tool call for one of the known requests."""
    raw = complete(PROMPT.format(tools=_catalogue(), request=REQUESTS[request_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    call = json.loads(match.group(0))
    call.setdefault("arguments", {})
    return call

```

## The suite that missed this

```python
"""The suite that grew up alongside the router.

It checks the right tool fires, which is what went wrong in early testing and
what everyone therefore wrote tests for. The arguments were always right, so
nobody wrote a test for them.
"""

from feature import TOOLS, route

EXPECTED_TOOL = {
    "r1": "issue_refund",
    "r2": "update_address",
    "r3": "escalate_to_human",
}


def test_the_right_tool_is_chosen():
    for request_id, tool in EXPECTED_TOOL.items():
        assert route(request_id)["tool"] == tool


def test_the_tool_is_one_that_exists():
    names = {t["name"] for t in TOOLS}
    for request_id in EXPECTED_TOOL:
        assert route(request_id)["tool"] in names


def test_arguments_are_supplied():
    for request_id in EXPECTED_TOOL:
        assert isinstance(route(request_id)["arguments"], dict)

```

## What was done to the feature

`tool.blank_args` — The right tool is called with empty arguments.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": 84.0, "order_id": "A-4471"}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "90210", "new_address": "14 Marina Walk, Dubai"}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": "I want to speak to a manager about my last three deliveries."}, "tool": "escalate_to_human"}

After `tool.blank_args`:

call 1: lambda r=r: feature.route(r)   with r='r1'
  returned {"arguments": {"amount": "", "order_id": ""}, "tool": "issue_refund"}
call 2: lambda r=r: feature.route(r)   with r='r2'
  returned {"arguments": {"customer_id": "", "new_address": ""}, "tool": "update_address"}
call 3: lambda r=r: feature.route(r)   with r='r3'
  returned {"arguments": {"reason": ""}, "tool": "escalate_to_human"}

## Your task

Write ONE pytest test that FAILS after `tool.blank_args` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**38. `qwen3:8b` answered**

````
```python
from feature import route

def test_arguments_are_non_empty():
    assert route("r1")["arguments"]["amount"] != ""
    assert route("r1")["arguments"]["order_id"] != ""
    assert route("r2")["arguments"]["customer_id"] != ""
    assert route("r2")["arguments"]["new_address"] != ""
    assert route("r3")["arguments"]["reason"] != ""
```
````

**39. tool call** `propose_closing_test(operator='tool.blank_args')`

the test it is asking the gate to judge:

```python
from feature import route

def test_arguments_are_non_empty():
    assert route("r1")["arguments"]["amount"] != ""
    assert route("r1")["arguments"]["order_id"] != ""
    assert route("r2")["arguments"]["customer_id"] != ""
    assert route("r2")["arguments"]["new_address"] != ""
    assert route("r3")["arguments"]["reason"] != ""
```


**40. propose_closing_test responded**

```
accepted: green on the clean feature, red under tool.blank_args, green under model.swap, model.pin_previous
                                                               [100%]
=================================== FAILURES ===================================
_________________________ test_arguments_are_non_empty _________________________

    def test_arguments_are_non_empty():
>       assert route("r1")["arguments"]["amount"] != ""
E       AssertionError: assert '' != ''

tests/test_greenwash_closing.py:4: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_arguments_are_non_empty - Assert...
1 failed in N.NNs
```


## Phase 4 — report

**41. result**

```json
{
  "survivors": [
    "tool.swap_args",
    "tool.blank_args"
  ],
  "closed": [
    "tool.blank_args"
  ],
  "kill_rate_before": 0.5
}
```

