"""Closing Tests the Auditor wrote for 11_document_reranker.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-11_document_reranker.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: rerank.identity — The ranker hands back the corpus in its original order, whatever was asked.
# gate: green on the clean feature, red under rerank.identity, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_q1_order_after_identity - Assert...
from feature import rank, QUERIES

def test_q1_order_after_identity():
    clean_q1 = ["d1", "d5", "d3", "d2", "d4"]
    identity_q1 = ["d1", "d2", "d3", "d4", "d5"]
    assert rank("q1") == clean_q1
    assert rank("q1") != identity_q1


# closes: rerank.reverse — The ranking is returned worst-first.
# gate: green on the clean feature, red under rerank.reverse, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_ranking_order_for_q1 - Assertion...
from feature import rank, QUERIES


def test_ranking_order_for_q1():
    expected = ["d1", "d5", "d3", "d2", "d4"]
    actual = rank("q1")
    assert actual == expected, f"Expected {expected}, got {actual}"
