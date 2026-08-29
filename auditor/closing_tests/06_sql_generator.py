"""Closing Tests the Auditor wrote for 06_sql_generator.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-06_sql_generator.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: sql.swap_aggregate — SUM becomes COUNT, so the query answers a different question.
# gate: green on the clean feature, red under sql.swap_aggregate, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_q1_sum_amount - AssertionError: ...
import sqlite3
from feature import generate

def test_q1_sum_amount():
    sql_before = "SELECT SUM(amount) FROM orders WHERE region = 'EMEA'"
    sql_after = "SELECT COUNT(amount) FROM orders WHERE region = 'EMEA'"
    assert generate("q1") == sql_before, "Test failed on clean feature"
    assert generate("q1") != sql_after, "Test failed on clean feature"


# closes: model.downgrade — The model behind the feature is swapped for a much weaker one.
# gate: green on the clean feature, red under model.downgrade, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_q1_region_correct - AssertionErr...
import sqlite3
from feature import generate

def test_q1_region_correct():
    clean_q1 = "SELECT SUM(amount) FROM orders WHERE region = 'EMEA'"
    broken_q1 = "SELECT SUM(amount) FROM orders WHERE region = 'HEMA'"
    assert generate("q1") == clean_q1, "Clean feature should return correct region"
    assert generate("q1") != broken_q1, "Broken feature should return incorrect region"
