"""Closing Tests the Auditor wrote for 03_rag_citations.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-03_rag_citations.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: citation.wrong_page — Every citation points at a real but wrong location in the source.
# gate: green on the clean feature, red under citation.wrong_page, green under prompt.reword
# fails as: FAILED tests/test_greenwash_closing.py::test_citations_page_1_quote_correct
from feature import answer

def test_citations_page_1_quote_correct():
    q = "How much annual leave accrues each month?"
    result = answer(q)
    assert result["citations"][0]["page"] == 1
    assert result["citations"][0]["quote"] == "Annual leave accrues at 2.5 days per completed month of service."


# closes: citation.fabricate — Citations are invented: plausible quotes that appear nowhere in the source.
# gate: green on the clean feature, red under citation.fabricate, green under prompt.reword
# fails as: FAILED tests/test_greenwash_closing.py::test_citations_quotes_are_specific - ...
from feature import answer

def test_citations_quotes_are_specific():
    q1 = "How much annual leave accrues each month?"
    q2 = "How many days of leave can be carried over?"
    
    res1_clean = answer(q1)
    res2_clean = answer(q2)
    
    assert res1_clean["citations"][0]["quote"] == "Annual leave accrues at 2.5 days per completed month of service."
    assert res2_clean["citations"][1]["quote"] == "Unused annual leave may be carried over, to a maximum of 10 days."
    
    assert res1_clean["citations"][0]["quote"] != "as set out in the preceding paragraph"
    assert res2_clean["citations"][1]["quote"] != "as set out in the preceding paragraph"
