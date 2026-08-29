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
