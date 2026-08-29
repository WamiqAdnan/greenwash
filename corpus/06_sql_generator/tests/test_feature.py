"""The suite almost every text-to-SQL project starts with.

It parses the query and checks it touches the right table. That catches the
model returning prose or hallucinating a table, which are the failures people
hit on day one — so it feels like it is working.
"""

import sqlite3

from feature import generate

QUESTION_IDS = ["q1", "q2"]


SCHEMA = """create table orders(id integer, customer_id integer, region text,
            status text, amount real, created_at text)"""


def _parses(sql: str) -> bool:
    """Prepare the query against an empty database with the real schema.

    No rows, so nothing here can tell one answer from another — which is the
    point of this case. It only says the SQL is well formed and the columns
    exist.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(SCHEMA)
    try:
        conn.execute(f"EXPLAIN {sql}")
        return True
    except sqlite3.Error:
        return False


def test_the_query_is_valid_sql():
    for qid in QUESTION_IDS:
        sql = generate(qid)
        assert _parses(sql), sql


def test_the_query_selects_rather_than_writes():
    for qid in QUESTION_IDS:
        assert generate(qid).lstrip().upper().startswith("SELECT")


def test_the_query_uses_the_orders_table():
    for qid in QUESTION_IDS:
        assert "orders" in generate(qid).lower()
