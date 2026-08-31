"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


# The same instruction asking for one more field — what `schema.add_field` swaps
# in. Both sample invoices print a subtotal, so this is a field the documents
# really carry and the extraction really can return. Widening the schema is the
# most ordinary change a team makes to a feature like this, and it does not make
# any previously correct answer wrong.
PROMPT_EXTRA_FIELD = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number),
subtotal (number).

Invoice:
{text}

JSON:"""


# The same instruction asking the model to say how sure it is — what
# `schema.add_confidence` swaps in. The other widening asks for a field the
# invoice prints; this one asks for a number the model makes up about its own
# work, which is the other half of how teams widen an extraction schema: you add
# a confidence so you can route the low ones to a human. Kept flat and asked for
# once, because a per-field confidence would nest the values that are already
# there and that would not be benign.
PROMPT_CONFIDENCE = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number),
confidence (a single top-level number between 0 and 1 — how sure you are of the
fields above; do not attach a confidence to each field).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data
