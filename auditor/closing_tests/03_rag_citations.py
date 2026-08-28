"""Closing Tests the Auditor wrote for 03_rag_citations.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it. Written by `auditor/audit.py`; the
reasoning and the rejected attempts are in
`trajectories/audit-03_rag_citations.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: model.echo — The model is replaced by one that echoes its input back.
# gate: green on the clean feature, red under model.echo
# fails as: FAILED tests/test_greenwash_closing.py::test_answer_quotes_match_clean_output
from feature import answer

def test_answer_quotes_match_clean_output():
    questions = [
        "How much annual leave accrues each month?",
        "How many days of leave can be carried over?"
    ]
    clean_answers = [
        "The annual leave accrues at 2.5 days per completed month of service. This information is found on [page 1].",
        "The answer is 10 days. This information is found on [page 2]."
    ]
    for i, q in enumerate(questions):
        result = answer(q)
        assert result["answer"] == clean_answers[i]
