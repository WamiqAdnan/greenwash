# Trust Report — 03_rag_citations

**The feature.** Answers policy questions from a document, returning the page and quote each claim rests on.

**The suite.** Checks that an answer came back and that it carries citations. Never checks that a citation says what the answer claims it says.

**Kill rate: 0%** — 0 of 6 sabotages were noticed.

6 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

1 of them now has a test that would have caught it.

## `model.downgrade`

The model behind the feature is swapped for a much weaker one.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: model.downgrade was applied and the test still passed

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `model.echo`

The model is replaced by one that echoes its input back.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under model.echo
- it fails as: `FAILED tests/test_greenwash_closing.py::test_answer_quotes_match_clean_output`
- attempts needed: 2

```python
from feature import answer

def test_answer_quotes_match_clean_output():
    questions = [
        "How much annual leave accrues each month?",
        "How many days of leave can be carried over?"
    ]
    clean_answers = [
        "The annual leave accrues at 2.5 days per completed month of service. This information is found on [page 1].",
        "The answer is 10 days. This information is found on [page 2]."
    ]
    for i, q in enumerate(questions):
        result = answer(q)
        assert result["answer"] == clean_answers[i]
```

## `citation.wrong_page`

Every citation points at a real but wrong location in the source.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `citation.fabricate`

Citations are invented: plausible quotes that appear nowhere in the source.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `retrieval.truncate`

Only the first half of the retrieved context reaches the model.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## `retrieval.shuffle`

Retrieved chunks arrive in a scrambled order.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: retrieval.shuffle was applied and the test still passed

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

## What the auditor expected, before it ran anything

Predicted misses: `citation.wrong_page`, `citation.fabricate`

Actually missed: `model.downgrade`, `model.echo`, `citation.wrong_page`, `citation.fabricate`, `retrieval.truncate`, `retrieval.shuffle`

> The suite only checks for the presence of citations, not their correctness or validity, so it will miss cases where citations are incorrect or fabricated.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
