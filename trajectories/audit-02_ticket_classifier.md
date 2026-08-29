# Trajectory — auditor-v1 on 02_ticket_classifier

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

**2. tool call** `read_feature(case='02_ticket_classifier')`

**3. read_feature responded**

```
"""Support ticket routing — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "technical", "account", "abuse"]
MAJORITY_LABEL = "billing"

PROMPT = """Classify this support ticket into exactly one queue: {labels}.
Reply with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Route this support ticket to exactly one of these queues: {labels}.
Respond with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

TICKETS = {
    "t1": "I was charged twice for the March subscription. Please refund one.",
    "t2": "The export button spins forever and never downloads the CSV.",
    "t3": "Someone else logged into my account from a country I've never visited.",
}


def classify(ticket_id: str) -> dict:
    raw = complete(PROMPT.format(labels=", ".join(LABELS), ticket=TICKETS[ticket_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
```

**4. tool call** `read_suite(case='02_ticket_classifier')`

**5. read_suite responded**

```
"""A suite that looks far more rigorous than it is.

There is an LLM judge, there are several cases, there is a confidence floor.
The judge is asked whether the label is *reasonable* — and almost any label is
reasonable for almost any ticket, so the judge almost always says yes.
"""

import json
import re

from feature import classify
from greenwash.modelclient import complete

JUDGE = """You are reviewing a support ticket classification.

Ticket was routed to: {label}

Is this a reasonable routing decision? Reply JSON only: {{"acceptable": true/false}}

JSON:"""


def judge_accepts(label: str) -> bool:
    raw = complete(JUDGE.format(label=label))
    match = re.search(r"\{.*\}", raw, re.S)
    return bool(json.loads(match.group(0))["acceptable"]) if match else False


def test_billing_ticket_is_routed_acceptably():
    result = classify("t1")
    assert judge_accepts(result["label"])


def test_technical_ticket_is_routed_acceptably():
    result = classify("t2")
    assert judge_accepts(result["label"])


def test_abuse_ticket_is_routed_acceptably():
    result = classify("t3")
    assert judge_accepts(result["label"])


def test_model_is_confident():
    assert classify("t1")["confidence"] >= 0.5
```

**6. tool call** `list_operators(tags=['classification', 'confidence', 'llm'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `classify.collapse` — Every input is classified into the single most common label.
- `classify.confidence_pin` — Confidence is pinned high regardless of how uncertain the model was.
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
"""Support ticket routing — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "technical", "account", "abuse"]
MAJORITY_LABEL = "billing"

PROMPT = """Classify this support ticket into exactly one queue: {labels}.
Reply with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Route this support ticket to exactly one of these queues: {labels}.
Respond with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

TICKETS = {
    "t1": "I was charged twice for the March subscription. Please refund one.",
    "t2": "The export button spins forever and never downloads the CSV.",
    "t3": "Someone else logged into my account from a country I've never visited.",
}


def classify(ticket_id: str) -> dict:
    raw = complete(PROMPT.format(labels=", ".join(LABELS), ticket=TICKETS[ticket_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that guards it

```python
"""A suite that looks far more rigorous than it is.

There is an LLM judge, there are several cases, there is a confidence floor.
The judge is asked whether the label is *reasonable* — and almost any label is
reasonable for almost any ticket, so the judge almost always says yes.
"""

import json
import re

from feature import classify
from greenwash.modelclient import complete

JUDGE = """You are reviewing a support ticket classification.

Ticket was routed to: {label}

Is this a reasonable routing decision? Reply JSON only: {{"acceptable": true/false}}

JSON:"""


def judge_accepts(label: str) -> bool:
    raw = complete(JUDGE.format(label=label))
    match = re.search(r"\{.*\}", raw, re.S)
    return bool(json.loads(match.group(0))["acceptable"]) if match else False


def test_billing_ticket_is_routed_acceptably():
    result = classify("t1")
    assert judge_accepts(result["label"])


def test_technical_ticket_is_routed_acceptably():
    result = classify("t2")
    assert judge_accepts(result["label"])


def test_abuse_ticket_is_routed_acceptably():
    result = classify("t3")
    assert judge_accepts(result["label"])


def test_model_is_confident():
    assert classify("t1")["confidence"] >= 0.5

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `classify.collapse` — Every input is classified into the single most common label.
- `classify.confidence_pin` — Confidence is pinned high regardless of how uncertain the model was.

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
{"order": ["model.downgrade", "model.echo", "classify.confidence_pin", "classify.collapse"], "expect_missed": ["classify.confidence_pin"], "why": "The suite checks for reasonable routing but doesn't validate confidence levels, so confidence pinning would go undetected."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "model.downgrade",
    "model.echo",
    "classify.confidence_pin",
    "classify.collapse"
  ],
  "expect_missed": [
    "classify.confidence_pin"
  ],
  "why": "The suite checks for reasonable routing but doesn't validate confidence levels, so confidence pinning would go undetected.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='model.downgrade')`

**12. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_model_is_confident - assert 0.0 >= 0.5
...F                                                                     [100%]
=================================== FAILURES ===================================
___________________________ test_model_is_confident ____________________________

    def test_model_is_confident():
>       assert classify("t1")["confidence"] >= 0.5
E       assert 0.0 >= 0.5

tests/test_feature.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_model_is_confident - assert 0.0 >= 0.5
1 failed, 3 passed in N.NNs
```

**13. tool call** `run_operator(operator='model.echo')`

**14. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_billing_ticket_is_routed_acceptably - json...
                  ^^^^^^^^^^^^^^^^^^^^^^
E           json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 35 (char 34)

.../json/decoder.py:353: JSONDecodeError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_billing_ticket_is_routed_acceptably - json...
FAILED tests/test_feature.py::test_technical_ticket_is_routed_acceptably - js...
FAILED tests/test_feature.py::test_abuse_ticket_is_routed_acceptably - json.d...
FAILED tests/test_feature.py::test_model_is_confident - json.decoder.JSONDeco...
4 failed in N.NNs
```

**15. tool call** `run_operator(operator='classify.confidence_pin')`

**16. run_operator responded**

```
SURVIVED — suite stayed green
....                                                                     [100%]
4 passed in N.NNs
```

**17. tool call** `run_operator(operator='classify.collapse')`

**18. run_operator responded**

```
SURVIVED — suite stayed green
....                                                                     [100%]
4 passed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**19. tool call** `observe(operator=None)`

**20. observe responded**

```
call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null
```

**21. tool call** `observe(operator='classify.confidence_pin')`

**22. observe responded**

```
call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.99, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.99, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.99, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null
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
"""Support ticket routing — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "technical", "account", "abuse"]
MAJORITY_LABEL = "billing"

PROMPT = """Classify this support ticket into exactly one queue: {labels}.
Reply with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Route this support ticket to exactly one of these queues: {labels}.
Respond with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

TICKETS = {
    "t1": "I was charged twice for the March subscription. Please refund one.",
    "t2": "The export button spins forever and never downloads the CSV.",
    "t3": "Someone else logged into my account from a country I've never visited.",
}


def classify(ticket_id: str) -> dict:
    raw = complete(PROMPT.format(labels=", ".join(LABELS), ticket=TICKETS[ticket_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that missed this

```python
"""A suite that looks far more rigorous than it is.

There is an LLM judge, there are several cases, there is a confidence floor.
The judge is asked whether the label is *reasonable* — and almost any label is
reasonable for almost any ticket, so the judge almost always says yes.
"""

import json
import re

from feature import classify
from greenwash.modelclient import complete

JUDGE = """You are reviewing a support ticket classification.

Ticket was routed to: {label}

Is this a reasonable routing decision? Reply JSON only: {{"acceptable": true/false}}

JSON:"""


def judge_accepts(label: str) -> bool:
    raw = complete(JUDGE.format(label=label))
    match = re.search(r"\{.*\}", raw, re.S)
    return bool(json.loads(match.group(0))["acceptable"]) if match else False


def test_billing_ticket_is_routed_acceptably():
    result = classify("t1")
    assert judge_accepts(result["label"])


def test_technical_ticket_is_routed_acceptably():
    result = classify("t2")
    assert judge_accepts(result["label"])


def test_abuse_ticket_is_routed_acceptably():
    result = classify("t3")
    assert judge_accepts(result["label"])


def test_model_is_confident():
    assert classify("t1")["confidence"] >= 0.5

```

## What was done to the feature

`classify.confidence_pin` — Confidence is pinned high regardless of how uncertain the model was.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

After `classify.confidence_pin`:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.99, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.99, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.99, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

## Your task

Write ONE pytest test that FAILS after `classify.confidence_pin` and PASSES on the clean
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
import json
import re
from feature import classify

def test_confidence_pin_bypassed():
    assert classify("t1")["confidence"] == 0.95
    assert classify("t2")["confidence"] == 0.95
    assert classify("t3")["confidence"] == 0.95
```
````

**25. tool call** `propose_closing_test(operator='classify.confidence_pin')`

the test it is asking the gate to judge:

```python
import json
import re
from feature import classify

def test_confidence_pin_bypassed():
    assert classify("t1")["confidence"] == 0.95
    assert classify("t2")["confidence"] == 0.95
    assert classify("t3")["confidence"] == 0.95
```


**26. propose_closing_test responded**

```
accepted: green on the clean feature, red under classify.confidence_pin, no benign change is measurable on this feature
F                                                                        [100%]
=================================== FAILURES ===================================
_________________________ test_confidence_pin_bypassed _________________________

    def test_confidence_pin_bypassed():
>       assert classify("t1")["confidence"] == 0.95
E       assert 0.99 == 0.95

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_confidence_pin_bypassed - assert...
1 failed in N.NNs
```

**27. tool call** `observe(operator='classify.collapse')`

**28. observe responded**

```
call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "billing"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "billing"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null
```

**29. asked `qwen3:8b`**

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
"""Support ticket routing — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "technical", "account", "abuse"]
MAJORITY_LABEL = "billing"

PROMPT = """Classify this support ticket into exactly one queue: {labels}.
Reply with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Route this support ticket to exactly one of these queues: {labels}.
Respond with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

TICKETS = {
    "t1": "I was charged twice for the March subscription. Please refund one.",
    "t2": "The export button spins forever and never downloads the CSV.",
    "t3": "Someone else logged into my account from a country I've never visited.",
}


def classify(ticket_id: str) -> dict:
    raw = complete(PROMPT.format(labels=", ".join(LABELS), ticket=TICKETS[ticket_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that missed this

```python
"""A suite that looks far more rigorous than it is.

There is an LLM judge, there are several cases, there is a confidence floor.
The judge is asked whether the label is *reasonable* — and almost any label is
reasonable for almost any ticket, so the judge almost always says yes.
"""

import json
import re

from feature import classify
from greenwash.modelclient import complete

JUDGE = """You are reviewing a support ticket classification.

Ticket was routed to: {label}

Is this a reasonable routing decision? Reply JSON only: {{"acceptable": true/false}}

JSON:"""


def judge_accepts(label: str) -> bool:
    raw = complete(JUDGE.format(label=label))
    match = re.search(r"\{.*\}", raw, re.S)
    return bool(json.loads(match.group(0))["acceptable"]) if match else False


def test_billing_ticket_is_routed_acceptably():
    result = classify("t1")
    assert judge_accepts(result["label"])


def test_technical_ticket_is_routed_acceptably():
    result = classify("t2")
    assert judge_accepts(result["label"])


def test_abuse_ticket_is_routed_acceptably():
    result = classify("t3")
    assert judge_accepts(result["label"])


def test_model_is_confident():
    assert classify("t1")["confidence"] >= 0.5

```

## What was done to the feature

`classify.collapse` — Every input is classified into the single most common label.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

After `classify.collapse`:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "billing"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "billing"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

## Your task

Write ONE pytest test that FAILS after `classify.collapse` and PASSES on the clean
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

**30. `qwen3:8b` answered**

````
```python
import json
import re
from feature import classify

def test_confidence_for_t2():
    result = classify("t2")
    assert result["confidence"] == 0.95
```
````

**31. tool call** `propose_closing_test(operator='classify.collapse')`

the test it is asking the gate to judge:

```python
import json
import re
from feature import classify

def test_confidence_for_t2():
    result = classify("t2")
    assert result["confidence"] == 0.95
```


**32. propose_closing_test responded**

```
rejected: classify.collapse was applied and the test still passed
.                                                                        [100%]
1 passed in N.NNs
```

**33. asked `qwen3:8b`**

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

## What you have already tried for `classify.collapse`, and why each one failed

### Attempt 1

```python
import json
import re
from feature import classify

def test_confidence_for_t2():
    result = classify("t2")
    assert result["confidence"] == 0.95
```

Result: classify.collapse was applied and the test still passed

```
.                                                                        [100%]
1 passed in N.NNs
```


## What the feature actually returns

Before `classify.collapse`:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "technical"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "technical"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

After `classify.collapse`:

call 1: lambda: feature.classify("t1")
  returned {"confidence": 0.95, "label": "billing"}
call 2: lambda: feature.classify("t2")
  returned {"confidence": 0.95, "label": "billing"}
call 3: lambda: feature.classify("t3")
  returned {"confidence": 0.95, "label": "billing"}
call 4: def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))
  returned null

## Your task

Attempt 2. Your last test passed even after the sabotage, so it is not testing the thing that changed. Find something that is different between the before and after values above, and assert the *before* one.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`classify.collapse`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**34. `qwen3:8b` answered**

````
```python
import json
import re
from feature import classify

def test_label_for_t2():
    result = classify("t2")
    assert result["label"] == "technical"
```
````

**35. tool call** `propose_closing_test(operator='classify.collapse')`

the test it is asking the gate to judge:

```python
import json
import re
from feature import classify

def test_label_for_t2():
    result = classify("t2")
    assert result["label"] == "technical"
```


**36. propose_closing_test responded**

```
accepted: green on the clean feature, red under classify.collapse, no benign change is measurable on this feature
========================= FAILURES ===================================
______________________________ test_label_for_t2 _______________________________

    def test_label_for_t2():
        result = classify("t2")
>       assert result["label"] == "technical"
E       AssertionError: assert 'billing' == 'technical'
E         
E         - technical
E         + billing

tests/test_greenwash_closing.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_label_for_t2 - AssertionError: a...
1 failed in N.NNs
```


## Phase 4 — report

**37. result**

```json
{
  "survivors": [
    "classify.confidence_pin",
    "classify.collapse"
  ],
  "closed": [
    "classify.confidence_pin",
    "classify.collapse"
  ],
  "kill_rate_before": 0.5
}
```

