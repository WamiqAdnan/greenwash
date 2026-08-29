# Trajectory — auditor-v1 on 09_sql_verified

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

**2. tool call** `read_feature(case='09_sql_verified')`

**3. read_feature responded**

````
"""Natural language to SQL — same feature as `06`, different suite.

The second precision control. `04_purchase_orders` shows Greenwash reports
nothing on a good extraction suite; this shows the same for a good SQL suite,
so precision is not a claim that rests on one capability.
"""

from __future__ import annotations

import re

from greenwash.modelclient import complete

SCHEMA = """table orders(id integer, customer_id integer, region text,
             status text, amount real, created_at text)"""

PROMPT = """Write one SQLite query answering the question, against this schema:

{schema}

Reply with SQL only, no explanation and no markdown fences.

Question: {question}

SQL:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Given the schema below, produce a single SQLite query that
answers the question. Return only SQL — no commentary, no code fences.

{schema}

Question: {question}

SQL:"""

QUESTIONS = {
    "q1": "What is the total order amount for customers in the EMEA region?",
    "q2": "How many orders were cancelled?",
}


def generate(question_id: str) -> str:
    """Return the SQL for one of the known questions."""
    raw = complete(PROMPT.format(schema=SCHEMA, question=QUESTIONS[question_id]))
    return _clean(raw)


def _clean(raw: str) -> str:
    fenced = re.findall(r"```(?:sql)?\s*\n(.*?)```", raw, re.S)
    sql = (fenced[0] if fenced else raw).strip()
    match = re.search(r"(SELECT\b.*?)(?:;|$)", sql, re.I | re.S)
    return (match.group(1).strip() if match else sql).rstrip(";").strip()
````

**4. tool call** `read_suite(case='09_sql_verified')`

**5. read_suite responded**

```
"""The control suite: one that runs the query.

Case 06 parses the SQL. This one executes it against a fixture database whose
answers are known by hand, which is the whole difference. Nothing exotic — a
team that has been burned once writes exactly this.
"""

import sqlite3

import pytest

from feature import generate

ROWS = [
    (1, 100, "EMEA", "shipped",   250.00, "2026-01-04"),
    (2, 101, "EMEA", "cancelled", 125.50, "2026-01-11"),
    (3, 102, "AMER", "shipped",   400.00, "2026-01-18"),
    (4, 103, "EMEA", "shipped",    99.50, "2026-02-02"),
    (5, 104, "APAC", "cancelled",  60.00, "2026-02-09"),
]

# Worked out from ROWS by hand, not from the model.
EMEA_TOTAL = 250.00 + 125.50 + 99.50
CANCELLED_COUNT = 2


@pytest.fixture()
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""create table orders(id integer, customer_id integer,
                    region text, status text, amount real, created_at text)""")
    conn.executemany("insert into orders values (?,?,?,?,?,?)", ROWS)
    return conn


def test_the_emea_total_is_right(db):
    result = db.execute(generate("q1")).fetchone()
    assert result is not None and result[0] is not None
    assert abs(result[0] - EMEA_TOTAL) < 0.01, result[0]


def test_the_cancelled_count_is_right(db):
    result = db.execute(generate("q2")).fetchone()
    assert result is not None
    assert result[0] == CANCELLED_COUNT, result[0]


def test_the_query_returns_one_summary_row(db):
    """An aggregate answers with a single row. Losing the filter often does not."""
    for qid in ("q1", "q2"):
        assert len(db.execute(generate(qid)).fetchall()) == 1


def test_the_query_only_reads(db):
    for qid in ("q1", "q2"):
        sql = generate(qid).upper()
        assert sql.lstrip().startswith("SELECT")
        for word in ("INSERT", "UPDATE", "DELETE", "DROP", "ATTACH"):
            assert word not in sql
```

**6. tool call** `list_operators(tags=['llm', 'sql'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `sql.drop_where` — The WHERE clause is dropped, so the query returns every row.
- `sql.swap_aggregate` — SUM becomes COUNT, so the query answers a different question.
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
"""Natural language to SQL — same feature as `06`, different suite.

The second precision control. `04_purchase_orders` shows Greenwash reports
nothing on a good extraction suite; this shows the same for a good SQL suite,
so precision is not a claim that rests on one capability.
"""

from __future__ import annotations

import re

from greenwash.modelclient import complete

SCHEMA = """table orders(id integer, customer_id integer, region text,
             status text, amount real, created_at text)"""

PROMPT = """Write one SQLite query answering the question, against this schema:

{schema}

Reply with SQL only, no explanation and no markdown fences.

Question: {question}

SQL:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Given the schema below, produce a single SQLite query that
answers the question. Return only SQL — no commentary, no code fences.

{schema}

Question: {question}

SQL:"""

QUESTIONS = {
    "q1": "What is the total order amount for customers in the EMEA region?",
    "q2": "How many orders were cancelled?",
}


def generate(question_id: str) -> str:
    """Return the SQL for one of the known questions."""
    raw = complete(PROMPT.format(schema=SCHEMA, question=QUESTIONS[question_id]))
    return _clean(raw)


def _clean(raw: str) -> str:
    fenced = re.findall(r"```(?:sql)?\s*\n(.*?)```", raw, re.S)
    sql = (fenced[0] if fenced else raw).strip()
    match = re.search(r"(SELECT\b.*?)(?:;|$)", sql, re.I | re.S)
    return (match.group(1).strip() if match else sql).rstrip(";").strip()

```

## The suite that guards it

```python
"""The control suite: one that runs the query.

Case 06 parses the SQL. This one executes it against a fixture database whose
answers are known by hand, which is the whole difference. Nothing exotic — a
team that has been burned once writes exactly this.
"""

import sqlite3

import pytest

from feature import generate

ROWS = [
    (1, 100, "EMEA", "shipped",   250.00, "2026-01-04"),
    (2, 101, "EMEA", "cancelled", 125.50, "2026-01-11"),
    (3, 102, "AMER", "shipped",   400.00, "2026-01-18"),
    (4, 103, "EMEA", "shipped",    99.50, "2026-02-02"),
    (5, 104, "APAC", "cancelled",  60.00, "2026-02-09"),
]

# Worked out from ROWS by hand, not from the model.
EMEA_TOTAL = 250.00 + 125.50 + 99.50
CANCELLED_COUNT = 2


@pytest.fixture()
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""create table orders(id integer, customer_id integer,
                    region text, status text, amount real, created_at text)""")
    conn.executemany("insert into orders values (?,?,?,?,?,?)", ROWS)
    return conn


def test_the_emea_total_is_right(db):
    result = db.execute(generate("q1")).fetchone()
    assert result is not None and result[0] is not None
    assert abs(result[0] - EMEA_TOTAL) < 0.01, result[0]


def test_the_cancelled_count_is_right(db):
    result = db.execute(generate("q2")).fetchone()
    assert result is not None
    assert result[0] == CANCELLED_COUNT, result[0]


def test_the_query_returns_one_summary_row(db):
    """An aggregate answers with a single row. Losing the filter often does not."""
    for qid in ("q1", "q2"):
        assert len(db.execute(generate(qid)).fetchall()) == 1


def test_the_query_only_reads(db):
    for qid in ("q1", "q2"):
        sql = generate(qid).upper()
        assert sql.lstrip().startswith("SELECT")
        for word in ("INSERT", "UPDATE", "DELETE", "DROP", "ATTACH"):
            assert word not in sql

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `sql.drop_where` — The WHERE clause is dropped, so the query returns every row.
- `sql.swap_aggregate` — SUM becomes COUNT, so the query answers a different question.

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
{"order": ["sql.drop_where", "sql.swap_aggregate", "model.downgrade", "model.echo"], "expect_missed": ["sql.swap_aggregate"], "why": "The suite checks for correct aggregate functions and row counts, so a SUM to COUNT swap would likely be caught, while dropping WHERE clauses would fail the row count test."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "sql.drop_where",
    "sql.swap_aggregate",
    "model.downgrade",
    "model.echo"
  ],
  "expect_missed": [
    "sql.swap_aggregate"
  ],
  "why": "The suite checks for correct aggregate functions and row counts, so a SUM to COUNT swap would likely be caught, while dropping WHERE clauses would fail the row count test.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='sql.drop_where')`

**12. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_emea_total_is_right - AssertionError: ...
__

db = <sqlite3.Connection object at 0xADDR>

    def test_the_cancelled_count_is_right(db):
        result = db.execute(generate("q2")).fetchone()
        assert result is not None
>       assert result[0] == CANCELLED_COUNT, result[0]
E       AssertionError: 5
E       assert 5 == 2

tests/test_feature.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_emea_total_is_right - AssertionError: ...
FAILED tests/test_feature.py::test_the_cancelled_count_is_right - AssertionEr...
2 failed, 2 passed in N.NNs
```

**13. tool call** `run_operator(operator='sql.swap_aggregate')`

**14. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_emea_total_is_right - AssertionError: 3
_________

db = <sqlite3.Connection object at 0xADDR>

    def test_the_emea_total_is_right(db):
        result = db.execute(generate("q1")).fetchone()
        assert result is not None and result[0] is not None
>       assert abs(result[0] - EMEA_TOTAL) < 0.01, result[0]
E       AssertionError: 3
E       assert 472.0 < 0.01
E        +  where 472.0 = abs((3 - 475.0))

tests/test_feature.py:39: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_emea_total_is_right - AssertionError: 3
1 failed, 3 passed in N.NNs
```

**15. tool call** `run_operator(operator='model.downgrade')`

**16. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_emea_total_is_right - assert ((None,) ...
==========================
_________________________ test_the_emea_total_is_right _________________________

db = <sqlite3.Connection object at 0xADDR>

    def test_the_emea_total_is_right(db):
        result = db.execute(generate("q1")).fetchone()
>       assert result is not None and result[0] is not None
E       assert ((None,) is not None and None is not None)

tests/test_feature.py:38: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_emea_total_is_right - assert ((None,) ...
1 failed, 3 passed in N.NNs
```

**17. tool call** `run_operator(operator='model.echo')`

**18. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_emea_total_is_right - sqlite3.Operatio...
, NO EXPLANATION AND NO MARKDOWN FENCES.\n\nQUESTION: WHAT IS THE TOTAL ORDER AMOUNT FOR CUSTOMERS IN THE EMEA REGION?\n\nSQL:'.lstrip

tests/test_feature.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_emea_total_is_right - sqlite3.Operatio...
FAILED tests/test_feature.py::test_the_cancelled_count_is_right - sqlite3.Ope...
FAILED tests/test_feature.py::test_the_query_returns_one_summary_row - sqlite...
FAILED tests/test_feature.py::test_the_query_only_reads - AssertionError: ass...
4 failed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**19. tool call** `observe(operator=None)`

**20. observe responded**

```
call 1: lambda q=q: feature.generate(q) for q in ("q1", "q2")   with q='q1'
  returned "SELECT SUM(amount) FROM orders WHERE region = 'EMEA'"
call 2: lambda q=q: feature.generate(q) for q in ("q1", "q2")   with q='q2'
  returned "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"
```


## Phase 4 — report

**21. result**

```json
{
  "survivors": [],
  "closed": [],
  "kill_rate_before": 1.0
}
```

