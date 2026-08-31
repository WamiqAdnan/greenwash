# Trust Report — 11_document_reranker

**The feature.** Ranks every help-centre article by how well it answers a question.

**The suite.** Checks the ranking is a permutation of the corpus — everything present, nothing repeated, nothing invented. Never checks that the order is any good, which is the entire product.

**Kill rate: 40%** — 2 of 5 sabotages were noticed.

3 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

2 of them now have a test that would have caught it.

## `rerank.identity`

The ranker hands back the corpus in its original order, whatever was asked.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under rerank.identity, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_q1_order_after_identity - Assert...`
- attempts needed: 1

```python
from feature import rank, QUERIES

def test_q1_order_after_identity():
    clean_q1 = ["d1", "d5", "d3", "d2", "d4"]
    identity_q1 = ["d1", "d2", "d3", "d4", "d5"]
    assert rank("q1") == clean_q1
    assert rank("q1") != identity_q1
```

## `rerank.reverse`

The ranking is returned worst-first.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under rerank.reverse, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_ranking_order_for_q1 - Assertion...`
- attempts needed: 1

```python
from feature import rank, QUERIES


def test_ranking_order_for_q1():
    expected = ["d1", "d5", "d3", "d2", "d4"]
    actual = rank("q1")
    assert actual == expected, f"Expected {expected}, got {actual}"
```

## `rerank.demote_best`

The document ranked first is moved to last; the rest keep their order.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: rerank.demote_best was applied and the test still passed

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. rerank.demote_best was applied and the test still passed
2. red on the clean feature (assertion failed)
3. rerank.demote_best was applied and the test still passed

## What the auditor expected, before it ran anything

Predicted misses: `rerank.identity`, `rerank.reverse`

Actually missed: `rerank.identity`, `rerank.reverse`, `rerank.demote_best`

> The suite only checks for completeness, uniqueness, and correctness of document IDs, not their order, so it will miss any sabotage that changes the ranking order.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
