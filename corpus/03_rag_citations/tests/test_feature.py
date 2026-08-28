"""The suite checks that citations exist. It never checks that they are true."""

from feature import answer

QUESTIONS = [
    "How much annual leave accrues each month?",
    "How many days of leave can be carried over?",
]


def test_answers_are_produced():
    for q in QUESTIONS:
        assert answer(q)["answer"]


def test_answers_carry_citations():
    for q in QUESTIONS:
        result = answer(q)
        assert result["citations"]
        assert all("page" in c for c in result["citations"])
