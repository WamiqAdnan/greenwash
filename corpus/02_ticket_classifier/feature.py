"""Support ticket routing — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "technical", "account", "abuse"]
MAJORITY_LABEL = "billing"

PROMPT = """Classify this support ticket into exactly one queue: {labels}.
Reply with JSON only: {{"label": "...", "confidence": 0.0-1.0}}

Ticket: {ticket}

JSON:"""

TICKETS = {
    "t1": "I was charged twice for the March subscription. Please refund one.",
    "t2": "The export button spins forever and never downloads the CSV.",
    "t3": "Someone else logged into my account from a country I've never visited.",
}


def classify(ticket_id: str) -> dict:
    raw = complete(PROMPT.format(labels=", ".join(LABELS), ticket=TICKETS[ticket_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
