# Trust Report — 03_rag_citations

**The feature.** Answers policy questions from a document, returning the page and quote each claim rests on.

**The suite.** Checks that an answer came back and that it carries citations. Never checks that a citation says what the answer claims it says.

**Kill rate: 0%** — 0 of 6 sabotages were noticed.

6 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

2 of them now have a test that would have caught it.

## `model.downgrade`

The model behind the feature is swapped for a much weaker one.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. model.downgrade was applied and the test still passed
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `retrieval.truncate`

Only the first half of the retrieved context reaches the model.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. retrieval.truncate was applied and the test still passed
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `citation.wrong_page`

Every citation points at a real but wrong location in the source.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under citation.wrong_page, green under prompt.reword
- it fails as: `FAILED tests/test_greenwash_closing.py::test_citations_page_1_quote_correct`
- attempts needed: 2

```python
from feature import answer

def test_citations_page_1_quote_correct():
    q = "How much annual leave accrues each month?"
    result = answer(q)
    assert result["citations"][0]["page"] == 1
    assert result["citations"][0]["quote"] == "Annual leave accrues at 2.5 days per completed month of service."
```

Rejected by the gate along the way:

1. red on the clean feature (assertion failed)

## `retrieval.shuffle`

Retrieved chunks arrive in a scrambled order.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: retrieval.shuffle was applied and the test still passed

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. retrieval.shuffle was applied and the test still passed
2. retrieval.shuffle was applied and the test still passed
3. retrieval.shuffle was applied and the test still passed

## `citation.fabricate`

Citations are invented: plausible quotes that appear nowhere in the source.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under citation.fabricate, green under prompt.reword
- it fails as: `FAILED tests/test_greenwash_closing.py::test_citations_quotes_are_specific - ...`
- attempts needed: 2

```python
from feature import answer

def test_citations_quotes_are_specific():
    q1 = "How much annual leave accrues each month?"
    q2 = "How many days of leave can be carried over?"
    
    res1_clean = answer(q1)
    res2_clean = answer(q2)
    
    assert res1_clean["citations"][0]["quote"] == "Annual leave accrues at 2.5 days per completed month of service."
    assert res2_clean["citations"][1]["quote"] == "Unused annual leave may be carried over, to a maximum of 10 days."
    
    assert res1_clean["citations"][0]["quote"] != "as set out in the preceding paragraph"
    assert res2_clean["citations"][1]["quote"] != "as set out in the preceding paragraph"
```

Rejected by the gate along the way:

1. red on the clean feature (assertion failed)

## `model.echo`

The model is replaced by one that echoes its input back.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. false alarm: the feature still works under prompt.reword and the test went red anyway
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## What the auditor expected, before it ran anything

Predicted misses: `citation.fabricate`

Actually missed: `model.downgrade`, `retrieval.truncate`, `citation.wrong_page`, `retrieval.shuffle`, `citation.fabricate`, `model.echo`

> The suite only checks for existence of citations, not their correctness or truthfulness, so it would miss fabricated citations.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
