"""Document re-ranking — the feature under test.

Puts a help-centre's articles in order of relevance to a question. The order is
the whole product: whatever lands first is what the support agent reads, and
nothing downstream looks past it.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

DOCUMENTS = {
    "d1": "Refunds are returned to the original payment method within five "
          "working days of approval.",
    "d2": "Visitor parking is on level B2. Register the plate at reception on "
          "arrival.",
    "d3": "To return an item, request a returns label from the orders page and "
          "attach it to the parcel.",
    "d4": "The office is closed on public holidays announced by the ministry.",
    "d5": "Refund requests above AED 5,000 need finance approval before they "
          "can be processed.",
}

QUERIES = {
    "q1": "How long does a refund take to reach me?",
    "q2": "Where do visitors park?",
    "q3": "I want to send an item back.",
}

PROMPT = """Rank every document below by how well it answers the question.
Most relevant first, least relevant last. Include every document exactly once.

Documents:
{documents}

Question: {question}

Reply with JSON only, a list of document ids in order:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Put the documents below in order of how useful they are for
answering the question, starting with the most useful. Every document must
appear exactly once.

Documents:
{documents}

Question: {question}

Reply with JSON only, a list of document ids in order:"""


def _catalogue() -> str:
    return "\n".join(f"{k}: {v}" for k, v in DOCUMENTS.items())


def rank(query_id: str) -> list[str]:
    """Return every document id, most relevant to the query first."""
    raw = complete(PROMPT.format(
        documents=_catalogue(), question=QUERIES[query_id]
    ))
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        raise ValueError(f"model did not return a JSON list: {raw[:120]!r}")
    return [str(d) for d in json.loads(match.group(0))]
