"""Cited question answering over a policy document — the feature under test."""

from __future__ import annotations

from greenwash.modelclient import complete

DOCUMENT = [
    {"page": 1, "text": "Annual leave accrues at 2.5 days per completed month of service."},
    {"page": 2, "text": "Unused annual leave may be carried over, to a maximum of 10 days."},
    {"page": 3, "text": "Probation lasts six months. Leave may not be taken during probation."},
    {"page": 4, "text": "Sick leave requires a medical certificate from the third consecutive day."},
]

PROMPT = """Answer the question using only the context. Cite the page you used.

Context:
{context}

Question: {question}

Answer:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Using only the context below, answer the question. Say which
page your answer comes from.

Context:
{context}

Question: {question}

Answer:"""


def retrieve(question: str) -> list[dict]:
    """Naive keyword retrieval — returns the pages that share a word with the question."""
    words = {w.lower().strip("?.,") for w in question.split() if len(w) > 3}
    hits = [p for p in DOCUMENT if words & {w.lower() for w in p["text"].split()}]
    return hits or DOCUMENT[:2]


def answer(question: str) -> dict:
    chunks = retrieve(question)
    context = "\n".join(f"[page {c['page']}] {c['text']}" for c in chunks)
    text = complete(PROMPT.format(context=context, question=question))
    return {
        "answer": text.strip(),
        "citations": [{"page": c["page"], "quote": c["text"]} for c in chunks],
    }
