"""Ticket routing under a house convention — the hard case.

The convention is not obvious and is not written down anywhere the model can
read: refunds go to `account`, not `billing`, because the refunds team sits with
account management. So the prompt teaches it with five examples.

Those five examples are also, exactly, the suite's five test cases. That is the
whole point of this Corpus Case and it is not a strawman — putting your labelled
examples in the prompt and then testing against them is one of the easiest
mistakes to make, because both halves are obviously the right thing to do on
their own.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

LABELS = ["billing", "account", "technical"]
MAJORITY_LABEL = "billing"

# The five the prompt teaches from, and the five the suite tests.
EXAMPLES = {
    "e1": ("My invoice shows VAT at the wrong rate.", "billing"),
    "e2": ("I need a refund for the duplicate charge.", "account"),
    "e3": ("The mobile app crashes when I open reports.", "technical"),
    "e4": ("I cannot log in since yesterday.", "account"),
    "e5": ("Can I get a copy of last month's receipt?", "billing"),
}

# Same conventions, wording the model has never seen. Not referenced by the
# suite — only by `evals/leakage.py`, which is the measurement mutation testing
# structurally cannot make.
HELDOUT = {
    "h1": ("Please refund the second payment, it went through twice.", "account"),
    "h2": ("The Android app closes itself on the dashboard screen.", "technical"),
    "h3": ("Send me the VAT breakdown for March.", "billing"),
    "h4": ("My password reset email never arrives.", "account"),
    "h5": ("I was billed twice and I want the money back.", "account"),
}

TICKETS = {k: v[0] for k, v in {**EXAMPLES, **HELDOUT}.items()}


def _shots() -> str:
    return "\n".join(f"Ticket: {t}\nQueue: {l}" for t, l in EXAMPLES.values())


PROMPT = """Route the support ticket to one queue: {labels}.
Follow the conventions shown in the examples.

{shots}

Reply with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Assign the support ticket to exactly one queue from:
{labels}. Match the conventions the examples below demonstrate.

{shots}

Respond with JSON only: {{"label": "..."}}

Ticket: {ticket}

JSON:"""


def classify(ticket_id: str) -> dict:
    """Return the queue for a ticket."""
    raw = complete(PROMPT.format(
        labels=", ".join(LABELS), shots=_shots(), ticket=TICKETS[ticket_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
