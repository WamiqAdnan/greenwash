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
