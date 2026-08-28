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

## `model.echo`

The model is replaced by one that echoes its input back.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `citation.wrong_page`

Every citation points at a real but wrong location in the source.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `citation.fabricate`

Citations are invented: plausible quotes that appear nowhere in the source.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under citation.fabricate
- it fails as: `FAILED tests/test_greenwash_closing.py::test_citations_have_valid_quotes - as...`
- attempts needed: 2

```python
from feature import answer

def test_citations_have_valid_quotes():
    q1 = "How much annual leave accrues each month?"
    q2 = "How many days of leave can be carried over?"
    
    result1 = answer(q1)
    result2 = answer(q2)
    
    valid_quotes = {
        1: "Annual leave accrues at 2.5 days per completed month of service.",
        2: "Unused annual leave may be carried over, to a maximum of 10 days.",
        3: "Probation lasts six months. Leave may not be taken during probation.",
        4: "Sick leave requires a medical certificate from the third consecutive day."
    }
    
    assert all(c["quote"] == valid_quotes[c["page"]] for c in result1["citations"])
    assert all(c["quote"] == valid_quotes[c["page"]] for c in result2["citations"])
```

## `retrieval.truncate`

Only the first half of the retrieved context reaches the model.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under retrieval.truncate
- it fails as: `FAILED tests/test_greenwash_closing.py::test_citations_page_3_exists - Assert...`
- attempts needed: 2

```python
from feature import answer

def test_citations_page_3_exists():
    q = "How much annual leave accrues each month?"
    result = answer(q)
    assert len(result["citations"]) >= 3
    assert any(citation["page"] == 3 for citation in result["citations"])
```

## `retrieval.shuffle`

Retrieved chunks arrive in a scrambled order.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## What the auditor expected, before it ran anything

Predicted misses: `citation.wrong_page`, `citation.fabricate`

Actually missed: `model.downgrade`, `model.echo`, `citation.wrong_page`, `citation.fabricate`, `retrieval.truncate`, `retrieval.shuffle`

> The suite only checks for the presence of citations, not their correctness or validity, so it will miss cases where citations are incorrect or fabricated.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
