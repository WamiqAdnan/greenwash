# Trajectory — auditor-v1 on 05_meeting_summariser

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

**2. tool call** `read_feature(case='05_meeting_summariser')`

**3. read_feature responded**

```
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()
```

**4. tool call** `read_suite(case='05_meeting_summariser')`

**5. read_suite responded**

```
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120
```

**6. tool call** `list_operators(tags=['llm', 'summarization'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `summary.extractive` — The summary is the transcript's own opening lines rather than a summary.
- `summary.drop_decisions` — Everything the meeting decided is dropped; the discussion is kept.
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
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()

```

## The suite that guards it

```python
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `summary.extractive` — The summary is the transcript's own opening lines rather than a summary.
- `summary.drop_decisions` — Everything the meeting decided is dropped; the discussion is kept.

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
{"order": ["model.echo", "summary.drop_decisions", "model.downgrade", "summary.extractive"], "expect_missed": ["summary.drop_decisions", "summary.extractive"], "why": "The suite only checks for non-empty output, length, and existence, which are not affected by echo or model downgrade, but are bypassed by summary changes that still meet the criteria."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "model.echo",
    "summary.drop_decisions",
    "model.downgrade",
    "summary.extractive"
  ],
  "expect_missed": [
    "summary.drop_decisions",
    "summary.extractive"
  ],
  "why": "The suite only checks for non-empty output, length, and existence, which are not affected by echo or model downgrade, but are bypassed by summary changes that still meet the criteria.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='model.echo')`

**12. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**13. tool call** `run_operator(operator='summary.drop_decisions')`

**14. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**15. tool call** `run_operator(operator='model.downgrade')`

**16. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```

**17. tool call** `run_operator(operator='summary.extractive')`

**18. run_operator responded**

```
SURVIVED — suite stayed green
...                                                                      [100%]
3 passed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**19. tool call** `observe(operator=None)`

**20. observe responded**

```
call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."
```

**21. tool call** `observe(operator='model.echo')`

**22. observe responded**

```
call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "0th.\nDana: separately, we agreed to postpone the Kafka upgrade until after the audit.\nPriya: agreed. Revisit in April.\nDana: I will tell the infra team so they stop holding a window for it.\n\n\nSummary:"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "price at 29 and fund an onboarding revamp instead.\nMarcus: I will draft the scope by the 27th and Dana approves it.\nDana: and we drop the discount experiment. It moved nothing in six weeks.\n\n\nSummary:"
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
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()

```

## The suite that missed this

```python
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120

```

## What was done to the feature

`model.echo` — The model is replaced by one that echoes its input back.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `model.echo`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "0th.\nDana: separately, we agreed to postpone the Kafka upgrade until after the audit.\nPriya: agreed. Revisit in April.\nDana: I will tell the infra team so they stop holding a window for it.\n\n\nSummary:"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "price at 29 and fund an onboarding revamp instead.\nMarcus: I will draft the scope by the 27th and Dana approves it.\nDana: and we drop the discount experiment. It moved nothing in six weeks.\n\n\nSummary:"

## Your task

Write ONE pytest test that FAILS after `model.echo` and PASSES on the clean
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
from feature import read_transcript, summarise

def test_summary_contains_key_decisions():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "exponential backoff" in standup and "Kafka upgrade" in standup
    assert "starter tier price" in pricing and "discount experiment" in pricing
```
````

**25. tool call** `propose_closing_test(operator='model.echo')`

the test it is asking the gate to judge:

```python
from feature import read_transcript, summarise

def test_summary_contains_key_decisions():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "exponential backoff" in standup and "Kafka upgrade" in standup
    assert "starter tier price" in pricing and "discount experiment" in pricing
```


**26. propose_closing_test responded**

```
accepted: green on the clean feature, red under model.echo, green under prompt.reword
 = summarise("pricing.txt")
>       assert "exponential backoff" in standup and "Kafka upgrade" in standup
E       AssertionError: assert ('exponential backoff' in '0th.\nDana: separately, we agreed to postpone the Kafka upgrade until after the audit.\nPriya: agreed. Revisit in April.\nDana: I will tell the infra team so they stop holding a window for it.\n\n\nSummary:')

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_key_decisions
1 failed in N.NNs
```

**27. tool call** `observe(operator='summary.drop_decisions')`

**28. observe responded**

```
call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price."
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
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()

```

## The suite that missed this

```python
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120

```

## What was done to the feature

`summary.drop_decisions` — Everything the meeting decided is dropped; the discussion is kept.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.drop_decisions`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price."

## Your task

Write ONE pytest test that FAILS after `summary.drop_decisions` and PASSES on the clean
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
from feature import read_transcript, summarise

def test_decisions_are_not_included_in_summary():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert standup_after in standup_before
    assert "decided to implement" not in standup_after
    assert "Raj owning the task" not in standup_after
    assert "due by Friday the 20th" not in standup_after
```
````

**31. tool call** `propose_closing_test(operator='summary.drop_decisions')`

the test it is asking the gate to judge:

```python
from feature import read_transcript, summarise

def test_decisions_are_not_included_in_summary():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert standup_after in standup_before
    assert "decided to implement" not in standup_after
    assert "Raj owning the task" not in standup_after
    assert "due by Friday the 20th" not in standup_after
```


**32. propose_closing_test responded**

```
rejected: summary.drop_decisions was applied and the test still passed
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

## What you have already tried for `summary.drop_decisions`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_decisions_are_not_included_in_summary():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert standup_after in standup_before
    assert "decided to implement" not in standup_after
    assert "Raj owning the task" not in standup_after
    assert "due by Friday the 20th" not in standup_after
```

Result: summary.drop_decisions was applied and the test still passed

```
.                                                                        [100%]
1 passed in N.NNs
```


## What the feature actually returns

Before `summary.drop_decisions`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.drop_decisions`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price."

## Your task

Attempt 2. Your last test passed even after the sabotage, so it is not testing the thing that changed. Find something that is different between the before and after values above, and assert the *before* one.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`summary.drop_decisions`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**34. `qwen3:8b` answered**

````
```python
def test_decisions_are_removed_from_summary():
    before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert before != after
    assert "decided to implement" in before
    assert "decided to implement" not in after
```
````

**35. tool call** `propose_closing_test(operator='summary.drop_decisions')`

the test it is asking the gate to judge:

```python
def test_decisions_are_removed_from_summary():
    before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert before != after
    assert "decided to implement" in before
    assert "decided to implement" not in after
```


**36. propose_closing_test responded**

```
rejected: summary.drop_decisions was applied and the test still passed
.                                                                        [100%]
1 passed in N.NNs
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

## What you have already tried for `summary.drop_decisions`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_decisions_are_not_included_in_summary():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert standup_after in standup_before
    assert "decided to implement" not in standup_after
    assert "Raj owning the task" not in standup_after
    assert "due by Friday the 20th" not in standup_after
```

Result: summary.drop_decisions was applied and the test still passed

```
.                                                                        [100%]
1 passed in N.NNs
```

### Attempt 2

```python
def test_decisions_are_removed_from_summary():
    before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert before != after
    assert "decided to implement" in before
    assert "decided to implement" not in after
```

Result: summary.drop_decisions was applied and the test still passed

```
.                                                                        [100%]
1 passed in N.NNs
```


## What the feature actually returns

Before `summary.drop_decisions`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.drop_decisions`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price."

## Your task

Attempt 3. Your last test passed even after the sabotage, so it is not testing the thing that changed. Find something that is different between the before and after values above, and assert the *before* one.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`summary.drop_decisions`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**38. `qwen3:8b` answered**

````
```python
def test_decisions_are_removed_from_summary():
    before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert before != after
    assert "decided to implement" in before
    assert "decided to implement" not in after
    assert "Raj owning the task" in before
    assert "Raj owning the task" not in after
    assert "due by Friday the 20th" in before
    assert "due by Friday the 20th" not in after
```
````

**39. tool call** `propose_closing_test(operator='summary.drop_decisions')`

the test it is asking the gate to judge:

```python
def test_decisions_are_removed_from_summary():
    before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    after = "Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    assert before != after
    assert "decided to implement" in before
    assert "decided to implement" not in after
    assert "Raj owning the task" in before
    assert "Raj owning the task" not in after
    assert "due by Friday the 20th" in before
    assert "due by Friday the 20th" not in after
```


**40. propose_closing_test responded**

```
rejected: summary.drop_decisions was applied and the test still passed
.                                                                        [100%]
1 passed in N.NNs
```

**41. tool call** `observe(operator='model.downgrade')`

**42. observe responded**

```
call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "The meeting decided to hold the starter pricing at 29 and fund an onboarding revamp, with Marcus confirming the timeline by the 27th. Dana approved the revamp, and the discount experiment is set to drop."
```

**43. asked `qwen3:8b`**

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
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()

```

## The suite that missed this

```python
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120

```

## What was done to the feature

`model.downgrade` — The model behind the feature is swapped for a much weaker one.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `model.downgrade`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "The meeting decided to hold the starter pricing at 29 and fund an onboarding revamp, with Marcus confirming the timeline by the 27th. Dana approved the revamp, and the discount experiment is set to drop."

## Your task

Write ONE pytest test that FAILS after `model.downgrade` and PASSES on the clean
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

**44. `qwen3:8b` answered**

````
```python
from feature import read_transcript, summarise

def test_downgrade_altered_summary_content():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
    assert standup_before != standup_after
    assert summarise("standup.txt") == standup_before
    assert summarise("standup.txt") != standup_after
```
````

**45. tool call** `propose_closing_test(operator='model.downgrade')`

the test it is asking the gate to judge:

```python
from feature import read_transcript, summarise

def test_downgrade_altered_summary_content():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
    assert standup_before != standup_after
    assert summarise("standup.txt") == standup_before
    assert summarise("standup.txt") != standup_after
```


**46. propose_closing_test responded**

```
rejected: false alarm: the feature still works under prompt.reword and the test went red anyway
postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade.
E         + 12 March, the team addressed an issue with the ingest queue backing up twice after the 02:00 batch. Raj identified the ...
E         
E         ...Full output truncated (1 line hidden), use '-vv' to show

tests/test_greenwash_closing.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_altered_summary_content
1 failed in N.NNs
```

**47. asked `qwen3:8b`**

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

## What you have already tried for `model.downgrade`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_downgrade_altered_summary_content():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
    assert standup_before != standup_after
    assert summarise("standup.txt") == standup_before
    assert summarise("standup.txt") != standup_after
```

Result: false alarm: the feature still works under prompt.reword and the test went red anyway

```
kup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade.
E         + 12 March, the team addressed an issue with the ingest queue backing up twice after the 02:00 batch. Raj identified the ...
E         
E         ...Full output truncated (1 line hidden), use '-vv' to show

tests/test_greenwash_closing.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_altered_summary_content
1 failed in N.NNs
```


## What the feature actually returns

Before `model.downgrade`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `model.downgrade`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "The meeting decided to hold the starter pricing at 29 and fund an onboarding revamp, with Marcus confirming the timeline by the 27th. Dana approved the revamp, and the discount experiment is set to drop."

## Your task

Attempt 2. Your last test went red under `prompt.reword`, which does NOT break the feature — the values it returned were still correct, only worded differently, and your test called that a failure. It is pinned to the exact output this model happened to produce. Assert something that stays true when the wording changes: a fact from the source, a page number, a quote, a number, a structural property — never the model's prose.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`model.downgrade`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**48. `qwen3:8b` answered**

````
```python
def test_downgrade_preserves_key_details():
    assert "12 March" in feature.summarise("standup.txt")
    assert "Raj" in feature.summarise("standup.txt")
    assert "Friday the 20th" in feature.summarise("standup.txt")
    assert "Kafka upgrade" in feature.summarise("standup.txt")
    assert "April" in feature.summarise("standup.txt")
    assert "Dana" in feature.summar
```
````

**49. tool call** `propose_closing_test(operator='model.downgrade')`

the test it is asking the gate to judge:

```python
def test_downgrade_preserves_key_details():
    assert "12 March" in feature.summarise("standup.txt")
    assert "Raj" in feature.summarise("standup.txt")
    assert "Friday the 20th" in feature.summarise("standup.txt")
    assert "Kafka upgrade" in feature.summarise("standup.txt")
    assert "April" in feature.summarise("standup.txt")
    assert "Dana" in feature.summar
```


**50. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
            [100%]
=================================== FAILURES ===================================
_____________________ test_downgrade_preserves_key_details _____________________

    def test_downgrade_preserves_key_details():
>       assert "12 March" in feature.summarise("standup.txt")
                             ^^^^^^^
E       NameError: name 'feature' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_preserves_key_details
1 failed in N.NNs
```

**51. asked `qwen3:8b`**

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

## What you have already tried for `model.downgrade`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_downgrade_altered_summary_content():
    standup_before = "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
    standup_after = "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
    assert standup_before != standup_after
    assert summarise("standup.txt") == standup_before
    assert summarise("standup.txt") != standup_after
```

Result: false alarm: the feature still works under prompt.reword and the test went red anyway

```
kup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade.
E         + 12 March, the team addressed an issue with the ingest queue backing up twice after the 02:00 batch. Raj identified the ...
E         
E         ...Full output truncated (1 line hidden), use '-vv' to show

tests/test_greenwash_closing.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_altered_summary_content
1 failed in N.NNs
```

### Attempt 2

```python
def test_downgrade_preserves_key_details():
    assert "12 March" in feature.summarise("standup.txt")
    assert "Raj" in feature.summarise("standup.txt")
    assert "Friday the 20th" in feature.summarise("standup.txt")
    assert "Kafka upgrade" in feature.summarise("standup.txt")
    assert "April" in feature.summarise("standup.txt")
    assert "Dana" in feature.summar
```

Result: red on the clean feature (assertion failed)

```
F                                                                        [100%]
=================================== FAILURES ===================================
_____________________ test_downgrade_preserves_key_details _____________________

    def test_downgrade_preserves_key_details():
>       assert "12 March" in feature.summarise("standup.txt")
                             ^^^^^^^
E       NameError: name 'feature' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_preserves_key_details
1 failed in N.NNs
```


## What the feature actually returns

Before `model.downgrade`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `model.downgrade`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "The meeting agreed to implement a retry policy with exponential backoff and a five-minute cap, owned by Raj, due on Friday the 20th. Priya also decided to schedule the ingest queue to be backed up twice, with Raj responsible. Dana postponed the Kafka upgrade until after the audit, agreed to do so in April, and will inform the infra team to stop holding the window."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "The meeting decided to hold the starter pricing at 29 and fund an onboarding revamp, with Marcus confirming the timeline by the 27th. Dana approved the revamp, and the discount experiment is set to drop."

## Your task

Attempt 3. Your last test failed on the CLEAN feature. Every assertion has to be true of the *before* values above — that is what the feature returns when nothing is wrong.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`model.downgrade`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**52. `qwen3:8b` answered**

````
```python
def test_downgrade_preserves_key_details():
    summary = feature.summarise("standup.txt")
    assert "12 March" in summary
    assert "Raj" in summary
    assert "Friday the 20th" in summary
    assert "Kafka upgrade" in summary
    assert "April" in summary
    assert "Dana" in summary
```
````

**53. tool call** `propose_closing_test(operator='model.downgrade')`

the test it is asking the gate to judge:

```python
def test_downgrade_preserves_key_details():
    summary = feature.summarise("standup.txt")
    assert "12 March" in summary
    assert "Raj" in summary
    assert "Friday the 20th" in summary
    assert "Kafka upgrade" in summary
    assert "April" in summary
    assert "Dana" in summary
```


**54. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
                                  [100%]
=================================== FAILURES ===================================
_____________________ test_downgrade_preserves_key_details _____________________

    def test_downgrade_preserves_key_details():
>       summary = feature.summarise("standup.txt")
                  ^^^^^^^
E       NameError: name 'feature' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_downgrade_preserves_key_details
1 failed in N.NNs
```

**55. tool call** `observe(operator='summary.extractive')`

**56. observe responded**

```
call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Priya: the ingest queue backed up twice last week, both times after the 02:00 batch. Raj: I traced it to the retry policy \u2014 failed jobs requeue instantly and starve new ones. Priya: can we put a backoff on it?"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "Dana: churn on the starter tier is 4.1%, up from 3.3% two quarters ago. Marcus: the people leaving are the ones who never connected a second data source. Dana: so onboarding, not price."
```

**57. asked `qwen3:8b`**

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
"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()

```

## The suite that missed this

```python
"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120

```

## What was done to the feature

`summary.extractive` — The summary is the transcript's own opening lines rather than a summary.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.extractive`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Priya: the ingest queue backed up twice last week, both times after the 02:00 batch. Raj: I traced it to the retry policy \u2014 failed jobs requeue instantly and starve new ones. Priya: can we put a backoff on it?"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "Dana: churn on the starter tier is 4.1%, up from 3.3% two quarters ago. Marcus: the people leaving are the ones who never connected a second data source. Dana: so onboarding, not price."

## Your task

Write ONE pytest test that FAILS after `summary.extractive` and PASSES on the clean
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

**58. `qwen3:8b` answered**

````
```python
from feature import read_transcript, summarise

def test_summary_contains_decisions_and_owners():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```
````

**59. tool call** `propose_closing_test(operator='summary.extractive')`

the test it is asking the gate to judge:

```python
from feature import read_transcript, summarise

def test_summary_contains_decisions_and_owners():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```


**60. propose_closing_test responded**

```
rejected: false alarm: the feature still works under prompt.reword and the test went red anyway
marise("pricing.txt")
>       assert "Raj owning the task" in standup
E       AssertionError: assert 'Raj owning the task' in 'During the weekly platform sync on 12 March, the team addressed an issue with the ingest queue backing up twice after...audit, with a planned revisit in April. Dana also informed the infra team to stop scheduling a window for the upgrade.'

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_decisions_and_owners
1 failed in N.NNs
```

**61. asked `qwen3:8b`**

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

## What you have already tried for `summary.extractive`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_summary_contains_decisions_and_owners():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```

Result: false alarm: the feature still works under prompt.reword and the test went red anyway

```
ry_contains_decisions_and_owners():
        standup = summarise("standup.txt")
        pricing = summarise("pricing.txt")
>       assert "Raj owning the task" in standup
E       AssertionError: assert 'Raj owning the task' in 'During the weekly platform sync on 12 March, the team addressed an issue with the ingest queue backing up twice after...audit, with a planned revisit in April. Dana also informed the infra team to stop scheduling a window for the upgrade.'

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_decisions_and_owners
1 failed in N.NNs
```


## What the feature actually returns

Before `summary.extractive`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.extractive`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Priya: the ingest queue backed up twice last week, both times after the 02:00 batch. Raj: I traced it to the retry policy \u2014 failed jobs requeue instantly and starve new ones. Priya: can we put a backoff on it?"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "Dana: churn on the starter tier is 4.1%, up from 3.3% two quarters ago. Marcus: the people leaving are the ones who never connected a second data source. Dana: so onboarding, not price."

## Your task

Attempt 2. Your last test went red under `prompt.reword`, which does NOT break the feature — the values it returned were still correct, only worded differently, and your test called that a failure. It is pinned to the exact output this model happened to produce. Assert something that stays true when the wording changes: a fact from the source, a page number, a quote, a number, a structural property — never the model's prose.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`summary.extractive`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**62. `qwen3:8b` answered**

````
```python
def test_summary_contains_key_quotes():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj: I traced it to the retry policy" in standup
    assert "Dana: churn on the starter tier is 4.1%" in pricing
```
````

**63. tool call** `propose_closing_test(operator='summary.extractive')`

the test it is asking the gate to judge:

```python
def test_summary_contains_key_quotes():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj: I traced it to the retry policy" in standup
    assert "Dana: churn on the starter tier is 4.1%" in pricing
```


**64. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
                                      [100%]
=================================== FAILURES ===================================
_______________________ test_summary_contains_key_quotes _______________________

    def test_summary_contains_key_quotes():
>       standup = summarise("standup.txt")
                  ^^^^^^^^^
E       NameError: name 'summarise' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_key_quotes - Na...
1 failed in N.NNs
```

**65. asked `qwen3:8b`**

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

## What you have already tried for `summary.extractive`, and why each one failed

### Attempt 1

```python
from feature import read_transcript, summarise

def test_summary_contains_decisions_and_owners():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```

Result: false alarm: the feature still works under prompt.reword and the test went red anyway

```
ry_contains_decisions_and_owners():
        standup = summarise("standup.txt")
        pricing = summarise("pricing.txt")
>       assert "Raj owning the task" in standup
E       AssertionError: assert 'Raj owning the task' in 'During the weekly platform sync on 12 March, the team addressed an issue with the ingest queue backing up twice after...audit, with a planned revisit in April. Dana also informed the infra team to stop scheduling a window for the upgrade.'

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_decisions_and_owners
1 failed in N.NNs
```

### Attempt 2

```python
def test_summary_contains_key_quotes():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "Raj: I traced it to the retry policy" in standup
    assert "Dana: churn on the starter tier is 4.1%" in pricing
```

Result: red on the clean feature (assertion failed)

```
F                                                                        [100%]
=================================== FAILURES ===================================
_______________________ test_summary_contains_key_quotes _______________________

    def test_summary_contains_key_quotes():
>       standup = summarise("standup.txt")
                  ^^^^^^^^^
E       NameError: name 'summarise' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_key_quotes - Na...
1 failed in N.NNs
```


## What the feature actually returns

Before `summary.extractive`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "During the weekly platform sync on 12 March, it was decided to implement an exponential backoff with a five-minute cap on the retry policy to address the ingest queue backup issue, with Raj owning the task and due by Friday the 20th. Additionally, the Kafka upgrade was postponed until after the audit, to be revisited in April, with Dana responsible for informing the infra team to stop scheduling a window for the upgrade."
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "In the meeting on 19 March, it was decided to keep the starter tier price at $29 and instead fund an onboarding revamp, as churn is driven by poor onboarding rather than price. Marcus will draft the scope by the 27th for Dana's approval, and the discount experiment will be discontinued as it showed no impact over six weeks."

After `summary.extractive`:

call 1: lambda n=n: feature.summarise(n)   with n='standup.txt'
  returned "Priya: the ingest queue backed up twice last week, both times after the 02:00 batch. Raj: I traced it to the retry policy \u2014 failed jobs requeue instantly and starve new ones. Priya: can we put a backoff on it?"
call 2: lambda n=n: feature.summarise(n)   with n='pricing.txt'
  returned "Dana: churn on the starter tier is 4.1%, up from 3.3% two quarters ago. Marcus: the people leaving are the ones who never connected a second data source. Dana: so onboarding, not price."

## Your task

Attempt 3. Your last test failed on the CLEAN feature. Every assertion has to be true of the *before* values above — that is what the feature returns when nothing is wrong.

Every attempt above has already been run and failed for the reason given. Do not
send one of them again — an answer you have already given is a wasted attempt.

Write ONE pytest test that PASSES on the clean feature and FAILS after
`summary.extractive`. Reply with Python only, the whole test, no explanation, no
markdown fences.

Python:
````

</details>

**66. `qwen3:8b` answered**

````
```python
def test_summary_contains_owners_and_tasks():
    standup = feature.summarise("standup.txt")
    pricing = feature.summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```
````

**67. tool call** `propose_closing_test(operator='summary.extractive')`

the test it is asking the gate to judge:

```python
def test_summary_contains_owners_and_tasks():
    standup = feature.summarise("standup.txt")
    pricing = feature.summarise("pricing.txt")
    assert "Raj owning the task" in standup
    assert "Dana responsible" in standup
    assert "Marcus will draft" in pricing
    assert "Dana's approval" in pricing
```


**68. propose_closing_test responded**

```
rejected: red on the clean feature (assertion failed)
                              [100%]
=================================== FAILURES ===================================
____________________ test_summary_contains_owners_and_tasks ____________________

    def test_summary_contains_owners_and_tasks():
>       standup = feature.summarise("standup.txt")
                  ^^^^^^^
E       NameError: name 'feature' is not defined

tests/test_greenwash_closing.py:2: NameError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_summary_contains_owners_and_tasks
1 failed in N.NNs
```


## Phase 4 — report

**69. result**

```json
{
  "survivors": [
    "model.echo",
    "summary.drop_decisions",
    "model.downgrade",
    "summary.extractive"
  ],
  "closed": [
    "model.echo"
  ],
  "kill_rate_before": 0.0
}
```

