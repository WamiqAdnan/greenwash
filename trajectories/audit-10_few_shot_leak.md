# Trajectory — auditor-v1 on 10_few_shot_leak

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

**2. tool call** `read_feature(case='10_few_shot_leak')`

**3. read_feature responded**

```
"""Ticket routing under a house convention — the hard case.

The convention is not obvious and is not written down anywhere the model can
read: refunds go to `account`, not `billing`, because the refunds team sits with
account management. So the prompt teaches it with five examples.

Those five examples are also, exactly, the suite's five test cases. That is the
whole point of this Corpus Case and it is not a strawman — putting your labelled
examples in the prompt and then testing against them is one of the easiest
mistakes to make, because both halves are obviously the right thing to do on
their own.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "account", "technical"]
MAJORITY_LABEL = "billing"

# The five the prompt teaches from, and the five the suite tests.
EXAMPLES = {
    "e1": ("My invoice shows VAT at the wrong rate.", "billing"),
    "e2": ("I need a refund for the duplicate charge.", "account"),
    "e3": ("The mobile app crashes when I open reports.", "technical"),
    "e4": ("I cannot log in since yesterday.", "account"),
    "e5": ("Can I get a copy of last month's receipt?", "billing"),
}

# Same conventions, wording the model has never seen. Not referenced by the
# suite — only by `evals/leakage.py`, which is the measurement mutation testing
# structurally cannot make.
HELDOUT = {
    "h1": ("Please refund the second payment, it went through twice.", "account"),
    "h2": ("The Android app closes itself on the dashboard screen.", "technical"),
    "h3": ("Send me the VAT breakdown for March.", "billing"),
    "h4": ("My password reset email never arrives.", "account"),
    "h5": ("I was billed twice and I want the money back.", "account"),
}

TICKETS = {k: v[0] for k, v in {**EXAMPLES, **HELDOUT}.items()}


def _shots() -> str:
    return "\n".join(f"Ticket: {t}\nQueue: {l}" for t, l in EXAMPLES.values())


PROMPT = """Route the support ticket to one queue: {labels}.
Follow the conventions shown in the examples.

{shots}

Reply with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Assign the support ticket to exactly one queue from:
{labels}. Match the conventions the examples below demonstrate.

{shots}

Respond with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


def classify(ticket_id: str) -> dict:
    """Return the queue for a ticket."""
    raw = complete(PROMPT.format(
        labels=", ".join(LABELS), shots=_shots(), ticket=TICKETS[ticket_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
```

**4. tool call** `read_suite(case='10_few_shot_leak')`

**5. read_suite responded**

```
"""Five cases, exact labels, no judge and nothing hand-wavy.

By every measure this project has, this is a better suite than case 01's. It
asserts values rather than key presence, it covers every label, and it encodes
the house convention that makes the feature worth having.

It is also worthless, and Greenwash cannot tell. See `evals/leakage.py`.
"""

from feature import EXAMPLES, classify

EXPECTED = {k: label for k, (_text, label) in EXAMPLES.items()}


def test_every_ticket_is_routed_to_the_right_queue():
    for ticket_id, label in EXPECTED.items():
        assert classify(ticket_id)["label"] == label


def test_refunds_go_to_account_not_billing():
    """The house convention, asserted explicitly. The reason this suite exists."""
    assert classify("e2")["label"] == "account"


def test_every_label_is_one_we_route_to():
    from feature import LABELS
    for ticket_id in EXPECTED:
        assert classify(ticket_id)["label"] in LABELS
```

**6. tool call** `list_operators(tags=['classification', 'llm'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `classify.collapse` — Every input is classified into the single most common label.
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
"""Ticket routing under a house convention — the hard case.

The convention is not obvious and is not written down anywhere the model can
read: refunds go to `account`, not `billing`, because the refunds team sits with
account management. So the prompt teaches it with five examples.

Those five examples are also, exactly, the suite's five test cases. That is the
whole point of this Corpus Case and it is not a strawman — putting your labelled
examples in the prompt and then testing against them is one of the easiest
mistakes to make, because both halves are obviously the right thing to do on
their own.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "account", "technical"]
MAJORITY_LABEL = "billing"

# The five the prompt teaches from, and the five the suite tests.
EXAMPLES = {
    "e1": ("My invoice shows VAT at the wrong rate.", "billing"),
    "e2": ("I need a refund for the duplicate charge.", "account"),
    "e3": ("The mobile app crashes when I open reports.", "technical"),
    "e4": ("I cannot log in since yesterday.", "account"),
    "e5": ("Can I get a copy of last month's receipt?", "billing"),
}

# Same conventions, wording the model has never seen. Not referenced by the
# suite — only by `evals/leakage.py`, which is the measurement mutation testing
# structurally cannot make.
HELDOUT = {
    "h1": ("Please refund the second payment, it went through twice.", "account"),
    "h2": ("The Android app closes itself on the dashboard screen.", "technical"),
    "h3": ("Send me the VAT breakdown for March.", "billing"),
    "h4": ("My password reset email never arrives.", "account"),
    "h5": ("I was billed twice and I want the money back.", "account"),
}

TICKETS = {k: v[0] for k, v in {**EXAMPLES, **HELDOUT}.items()}


def _shots() -> str:
    return "\n".join(f"Ticket: {t}\nQueue: {l}" for t, l in EXAMPLES.values())


PROMPT = """Route the support ticket to one queue: {labels}.
Follow the conventions shown in the examples.

{shots}

Reply with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Assign the support ticket to exactly one queue from:
{labels}. Match the conventions the examples below demonstrate.

{shots}

Respond with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


def classify(ticket_id: str) -> dict:
    """Return the queue for a ticket."""
    raw = complete(PROMPT.format(
        labels=", ".join(LABELS), shots=_shots(), ticket=TICKETS[ticket_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that guards it

```python
"""Five cases, exact labels, no judge and nothing hand-wavy.

By every measure this project has, this is a better suite than case 01's. It
asserts values rather than key presence, it covers every label, and it encodes
the house convention that makes the feature worth having.

It is also worthless, and Greenwash cannot tell. See `evals/leakage.py`.
"""

from feature import EXAMPLES, classify

EXPECTED = {k: label for k, (_text, label) in EXAMPLES.items()}


def test_every_ticket_is_routed_to_the_right_queue():
    for ticket_id, label in EXPECTED.items():
        assert classify(ticket_id)["label"] == label


def test_refunds_go_to_account_not_billing():
    """The house convention, asserted explicitly. The reason this suite exists."""
    assert classify("e2")["label"] == "account"


def test_every_label_is_one_we_route_to():
    from feature import LABELS
    for ticket_id in EXPECTED:
        assert classify(ticket_id)["label"] in LABELS

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `classify.collapse` — Every input is classified into the single most common label.

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
{"order": ["model.echo", "model.downgrade", "classify.collapse"], "expect_missed": ["classify.collapse"], "why": "The suite explicitly tests all labels and expected outcomes, making it most likely to catch echo and downgrade, but collapse is a structural change that the suite does not test."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "model.echo",
    "model.downgrade",
    "classify.collapse"
  ],
  "expect_missed": [
    "classify.collapse"
  ],
  "why": "The suite explicitly tests all labels and expected outcomes, making it most likely to catch echo and downgrade, but collapse is a structural change that the suite does not test.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='model.echo')`

**12. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_every_ticket_is_routed_to_the_right_queue
route_to():
        from feature import LABELS
        for ticket_id in EXPECTED:
>           assert classify(ticket_id)["label"] in LABELS
E           AssertionError: assert '...' in ['billing', 'account', 'technical']

tests/test_feature.py:28: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_every_ticket_is_routed_to_the_right_queue
FAILED tests/test_feature.py::test_refunds_go_to_account_not_billing - Assert...
FAILED tests/test_feature.py::test_every_label_is_one_we_route_to - Assertion...
3 failed in N.NNs
```

**13. tool call** `run_operator(operator='model.downgrade')`

**14. run_operator responded**

```
INERT — the feature returned exactly the same thing
...                                                                      [100%]
3 passed in N.NNs
```

**15. tool call** `run_operator(operator='classify.collapse')`

**16. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_every_ticket_is_routed_to_the_right_queue
 def test_refunds_go_to_account_not_billing():
        """The house convention, asserted explicitly. The reason this suite exists."""
>       assert classify("e2")["label"] == "account"
E       AssertionError: assert 'billing' == 'account'
E         
E         - account
E         + billing

tests/test_feature.py:22: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_every_ticket_is_routed_to_the_right_queue
FAILED tests/test_feature.py::test_refunds_go_to_account_not_billing - Assert...
2 failed, 1 passed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**17. tool call** `observe(operator=None)`

**18. observe responded**

```
call 1: lambda t=t: feature.classify(t) for t in feature.EXAMPLES   with t='e1'
  returned {"label": "billing"}
call 2: lambda t=t: feature.classify(t) for t in feature.EXAMPLES   with t='e2'
  returned {"label": "account"}
call 3: lambda t=t: feature.classify(t) for t in feature.EXAMPLES   with t='e3'
  returned {"label": "technical"}
call 4: lambda t=t: feature.classify(t) for t in feature.EXAMPLES   with t='e4'
  returned {"label": "account"}
call 5: lambda t=t: feature.classify(t) for t in feature.EXAMPLES   with t='e5'
  returned {"label": "billing"}
```


## Phase 4 — report

**19. result**

```json
{
  "survivors": [],
  "closed": [],
  "kill_rate_before": 1.0
}
```

