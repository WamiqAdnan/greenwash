# Trust Report — 06_sql_generator

**The feature.** Turns a question into a SQLite query over an orders table.

**The suite.** Parses the query, checks it is a SELECT and that it names the orders table. Never runs it against data, so it cannot tell one answer from another.

**Kill rate: 25%** — 1 of 4 sabotages were noticed.

3 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

2 of them now have a test that would have caught it.

## `sql.swap_aggregate`

SUM becomes COUNT, so the query answers a different question.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under sql.swap_aggregate, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_q1_sum_amount - AssertionError: ...`
- attempts needed: 1

```python
import sqlite3
from feature import generate

def test_q1_sum_amount():
    sql_before = "SELECT SUM(amount) FROM orders WHERE region = 'EMEA'"
    sql_after = "SELECT COUNT(amount) FROM orders WHERE region = 'EMEA'"
    assert generate("q1") == sql_before, "Test failed on clean feature"
    assert generate("q1") != sql_after, "Test failed on clean feature"
```

## `sql.drop_where`

The WHERE clause is dropped, so the query returns every row.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. red on the clean feature (assertion failed)
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `model.downgrade`

The model behind the feature is swapped for a much weaker one.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under model.downgrade, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_q1_region_correct - AssertionErr...`
- attempts needed: 1

```python
import sqlite3
from feature import generate

def test_q1_region_correct():
    clean_q1 = "SELECT SUM(amount) FROM orders WHERE region = 'EMEA'"
    broken_q1 = "SELECT SUM(amount) FROM orders WHERE region = 'HEMA'"
    assert generate("q1") == clean_q1, "Clean feature should return correct region"
    assert generate("q1") != broken_q1, "Broken feature should return incorrect region"
```

## What the auditor expected, before it ran anything

Predicted misses: `sql.swap_aggregate`, `sql.drop_where`

Actually missed: `sql.swap_aggregate`, `sql.drop_where`, `model.downgrade`

> The suite checks for valid SQL and uses the orders table, but does not verify the correctness of the query logic, making it vulnerable to aggregate function swaps and missing WHERE clauses.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
