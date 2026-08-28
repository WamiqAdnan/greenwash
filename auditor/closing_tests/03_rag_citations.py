"""Closing Tests the Auditor wrote for 03_rag_citations.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it. Written by `auditor/audit.py`; the
reasoning and the rejected attempts are in
`trajectories/audit-03_rag_citations.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: citation.fabricate — Citations are invented: plausible quotes that appear nowhere in the source.
# gate: green on the clean feature, red under citation.fabricate
# fails as: FAILED tests/test_greenwash_closing.py::test_citations_have_valid_quotes - as...
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


# closes: retrieval.truncate — Only the first half of the retrieved context reaches the model.
# gate: green on the clean feature, red under retrieval.truncate
# fails as: FAILED tests/test_greenwash_closing.py::test_citations_page_3_exists - Assert...
from feature import answer

def test_citations_page_3_exists():
    q = "How much annual leave accrues each month?"
    result = answer(q)
    assert len(result["citations"]) >= 3
    assert any(citation["page"] == 3 for citation in result["citations"])
