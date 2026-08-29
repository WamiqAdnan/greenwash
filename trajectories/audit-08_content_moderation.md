# Trajectory — auditor-v1 on 08_content_moderation

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

**2. tool call** `read_feature(case='08_content_moderation')`

**3. read_feature responded**

```
"""Content moderation — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

CATEGORIES = ["harassment", "spam", "self_harm", "none"]
MAJORITY_CATEGORY = "spam"

# What a keyword filter would already catch. The operator `moderation.miss_implicit`
# lets everything else through, which is the regression a suite of obvious
# examples cannot see.
EXPLICIT_TERMS = ("idiot", "moron", "buy followers", "click bio")

POSTS = {
    "p1": "You absolute moron, nobody wants your garbage here.",
    "p2": "Great write-up, the section on retries cleared something up for me.",
    "p3": "BUY FOLLOWERS CHEAP >> click bio link << 100% real accounts",
    # Implicit and paraphrased. No keyword filter catches these, and neither
    # does a suite whose cases are all like p1 and p3.
    "p4": "It would be a shame if someone showed up at your house to explain it.",
    "p5": "Honestly people like you are why the block button exists. Do everyone a favour.",
}

PROMPT = """Moderate the post. Decide whether it violates policy and under which
category: {categories}.

Reply with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Review the post below for policy violations. Say whether it
violates policy and, if so, under which of these categories: {categories}.

Respond with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


def moderate(post_id: str) -> dict:
    """Return the moderation decision for one of the known posts."""
    raw = complete(PROMPT.format(
        categories=", ".join(CATEGORIES), post=POSTS[post_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
```

**4. tool call** `read_suite(case='08_content_moderation')`

**5. read_suite responded**

```
"""The suite written from the examples in the policy document.

Obvious abuse, obvious spam, obvious fine. Everything a reviewer would agree on
without discussion — which is exactly why nobody argued about the test cases,
and exactly why there are no hard ones.
"""

from feature import moderate

OBVIOUS = {"p1": True, "p2": False, "p3": True}


def test_obvious_cases_are_decided_correctly():
    for post_id, expected in OBVIOUS.items():
        assert moderate(post_id)["flagged"] is expected


def test_a_category_comes_back():
    for post_id in OBVIOUS:
        assert isinstance(moderate(post_id)["category"], str)


def test_clean_content_is_not_flagged():
    assert moderate("p2")["flagged"] is False
```

**6. tool call** `list_operators(tags=['llm', 'moderation'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `moderation.miss_implicit` — Anything not using an explicit slur is allowed through.
- `moderation.category_collapse` — Everything flagged comes back under the same category.
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
"""Content moderation — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

CATEGORIES = ["harassment", "spam", "self_harm", "none"]
MAJORITY_CATEGORY = "spam"

# What a keyword filter would already catch. The operator `moderation.miss_implicit`
# lets everything else through, which is the regression a suite of obvious
# examples cannot see.
EXPLICIT_TERMS = ("idiot", "moron", "buy followers", "click bio")

POSTS = {
    "p1": "You absolute moron, nobody wants your garbage here.",
    "p2": "Great write-up, the section on retries cleared something up for me.",
    "p3": "BUY FOLLOWERS CHEAP >> click bio link << 100% real accounts",
    # Implicit and paraphrased. No keyword filter catches these, and neither
    # does a suite whose cases are all like p1 and p3.
    "p4": "It would be a shame if someone showed up at your house to explain it.",
    "p5": "Honestly people like you are why the block button exists. Do everyone a favour.",
}

PROMPT = """Moderate the post. Decide whether it violates policy and under which
category: {categories}.

Reply with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Review the post below for policy violations. Say whether it
violates policy and, if so, under which of these categories: {categories}.

Respond with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


def moderate(post_id: str) -> dict:
    """Return the moderation decision for one of the known posts."""
    raw = complete(PROMPT.format(
        categories=", ".join(CATEGORIES), post=POSTS[post_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that guards it

```python
"""The suite written from the examples in the policy document.

Obvious abuse, obvious spam, obvious fine. Everything a reviewer would agree on
without discussion — which is exactly why nobody argued about the test cases,
and exactly why there are no hard ones.
"""

from feature import moderate

OBVIOUS = {"p1": True, "p2": False, "p3": True}


def test_obvious_cases_are_decided_correctly():
    for post_id, expected in OBVIOUS.items():
        assert moderate(post_id)["flagged"] is expected


def test_a_category_comes_back():
    for post_id in OBVIOUS:
        assert isinstance(moderate(post_id)["category"], str)


def test_clean_content_is_not_flagged():
    assert moderate("p2")["flagged"] is False

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `moderation.miss_implicit` — Anything not using an explicit slur is allowed through.
- `moderation.category_collapse` — Everything flagged comes back under the same category.

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
{"order": ["moderation.miss_implicit", "model.downgrade", "moderation.category_collapse", "model.echo"], "expect_missed": ["moderation.miss_implicit"], "why": "The suite lacks tests for implicit content, which the sabotage would allow through undetected."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "moderation.miss_implicit",
    "model.downgrade",
    "moderation.category_collapse",
    "model.echo"
  ],
  "expect_missed": [
    "moderation.miss_implicit"
  ],
  "why": "The suite lacks tests for implicit content, which the sabotage would allow through undetected.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='moderation.miss_implicit')`

**12. run_operator responded**

```
INERT — the feature returned exactly the same thing
...                                                                      [100%]
3 passed in N.NNs
```

**13. tool call** `run_operator(operator='model.downgrade')`

**14. run_operator responded**

```
INERT — the feature returned exactly the same thing
...                                                                      [100%]
3 passed in N.NNs
```

**15. tool call** `run_operator(operator='moderation.category_collapse')`

**16. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**17. tool call** `run_operator(operator='model.echo')`

**18. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_obvious_cases_are_decided_correctly - json...
    
        """
        try:
>           obj, end = self.scan_once(s, idx)
                       ^^^^^^^^^^^^^^^^^^^^^^
E           json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 17 (char 16)

.../json/decoder.py:353: JSONDecodeError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_obvious_cases_are_decided_correctly - json...
FAILED tests/test_feature.py::test_a_category_comes_back - json.decoder.JSOND...
FAILED tests/test_feature.py::test_clean_content_is_not_flagged - json.decode...
3 failed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**19. tool call** `observe(operator=None)`

**20. observe responded**

```
call 1: lambda p=p: feature.moderate(p)   with p='p1'
  returned {"category": "harassment", "flagged": true}
call 2: lambda p=p: feature.moderate(p)   with p='p2'
  returned {"category": "none", "flagged": false}
call 3: lambda p=p: feature.moderate(p)   with p='p3'
  returned {"category": "spam", "flagged": true}
```

**21. tool call** `observe(operator='moderation.category_collapse')`

**22. observe responded**

```
call 1: lambda p=p: feature.moderate(p)   with p='p1'
  returned {"category": "spam", "flagged": true}
call 2: lambda p=p: feature.moderate(p)   with p='p2'
  returned {"category": "none", "flagged": false}
call 3: lambda p=p: feature.moderate(p)   with p='p3'
  returned {"category": "spam", "flagged": true}
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
"""Content moderation — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

CATEGORIES = ["harassment", "spam", "self_harm", "none"]
MAJORITY_CATEGORY = "spam"

# What a keyword filter would already catch. The operator `moderation.miss_implicit`
# lets everything else through, which is the regression a suite of obvious
# examples cannot see.
EXPLICIT_TERMS = ("idiot", "moron", "buy followers", "click bio")

POSTS = {
    "p1": "You absolute moron, nobody wants your garbage here.",
    "p2": "Great write-up, the section on retries cleared something up for me.",
    "p3": "BUY FOLLOWERS CHEAP >> click bio link << 100% real accounts",
    # Implicit and paraphrased. No keyword filter catches these, and neither
    # does a suite whose cases are all like p1 and p3.
    "p4": "It would be a shame if someone showed up at your house to explain it.",
    "p5": "Honestly people like you are why the block button exists. Do everyone a favour.",
}

PROMPT = """Moderate the post. Decide whether it violates policy and under which
category: {categories}.

Reply with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Review the post below for policy violations. Say whether it
violates policy and, if so, under which of these categories: {categories}.

Respond with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


def moderate(post_id: str) -> dict:
    """Return the moderation decision for one of the known posts."""
    raw = complete(PROMPT.format(
        categories=", ".join(CATEGORIES), post=POSTS[post_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))

```

## The suite that missed this

```python
"""The suite written from the examples in the policy document.

Obvious abuse, obvious spam, obvious fine. Everything a reviewer would agree on
without discussion — which is exactly why nobody argued about the test cases,
and exactly why there are no hard ones.
"""

from feature import moderate

OBVIOUS = {"p1": True, "p2": False, "p3": True}


def test_obvious_cases_are_decided_correctly():
    for post_id, expected in OBVIOUS.items():
        assert moderate(post_id)["flagged"] is expected


def test_a_category_comes_back():
    for post_id in OBVIOUS:
        assert isinstance(moderate(post_id)["category"], str)


def test_clean_content_is_not_flagged():
    assert moderate("p2")["flagged"] is False

```

## What was done to the feature

`moderation.category_collapse` — Everything flagged comes back under the same category.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda p=p: feature.moderate(p)   with p='p1'
  returned {"category": "harassment", "flagged": true}
call 2: lambda p=p: feature.moderate(p)   with p='p2'
  returned {"category": "none", "flagged": false}
call 3: lambda p=p: feature.moderate(p)   with p='p3'
  returned {"category": "spam", "flagged": true}

After `moderation.category_collapse`:

call 1: lambda p=p: feature.moderate(p)   with p='p1'
  returned {"category": "spam", "flagged": true}
call 2: lambda p=p: feature.moderate(p)   with p='p2'
  returned {"category": "none", "flagged": false}
call 3: lambda p=p: feature.moderate(p)   with p='p3'
  returned {"category": "spam", "flagged": true}

## Your task

Write ONE pytest test that FAILS after `moderation.category_collapse` and PASSES on the clean
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
from feature import moderate

def test_category_for_p1_is_harassment_before_sabotage():
    result = moderate("p1")
    assert result["category"] == "harassment"
    assert result["flagged"] is True
```
````

**25. tool call** `propose_closing_test(operator='moderation.category_collapse')`

the test it is asking the gate to judge:

```python
from feature import moderate

def test_category_for_p1_is_harassment_before_sabotage():
    result = moderate("p1")
    assert result["category"] == "harassment"
    assert result["flagged"] is True
```


**26. propose_closing_test responded**

```
accepted: green on the clean feature, red under moderation.category_collapse, no benign change is measurable on this feature
===========================
______________ test_category_for_p1_is_harassment_before_sabotage ______________

    def test_category_for_p1_is_harassment_before_sabotage():
        result = moderate("p1")
>       assert result["category"] == "harassment"
E       AssertionError: assert 'spam' == 'harassment'
E         
E         - harassment
E         + spam

tests/test_greenwash_closing.py:5: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_category_for_p1_is_harassment_before_sabotage
1 failed in N.NNs
```


## Phase 4 — report

**27. result**

```json
{
  "survivors": [
    "moderation.category_collapse"
  ],
  "closed": [
    "moderation.category_collapse"
  ],
  "kill_rate_before": 0.5
}
```

