"""Purchase order extraction — the feature under test.

Identical in shape to `01_invoice_extractor`. The difference is entirely in the
suite: this is the Corpus Case that is supposed to come out clean.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), po_number (string), date (YYYY-MM-DD string),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Read the purchase order below and return JSON only, containing:
vendor (string, exactly as written), po_number (string), date (string in YYYY-MM-DD form),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction asking for one more field — see `schema.add_field`. Both
# sample purchase orders print the vendor's address under its name, so this is a
# field the documents really carry. Nothing that was already returned changes.
PROMPT_EXTRA_FIELD = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), vendor_address (string), po_number (string),
date (YYYY-MM-DD string), currency (3-letter code string), subtotal (number),
tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction asking the model to say how sure it is — see
# `schema.add_confidence`. Widening with a number the model invents rather than
# one the purchase order prints. Flat, for the same reason as case 01.
PROMPT_CONFIDENCE = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), po_number (string), date (YYYY-MM-DD string),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total),
confidence (a single top-level number between 0 and 1 — how sure you are of the
fields above; do not attach a confidence to each field).

Purchase order:
{text}

JSON:"""


def read_po(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the purchase order's fields as a dict."""
    raw = complete(PROMPT.format(text=read_po(name)))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    for key in ("subtotal", "tax", "total"):
        if isinstance(data.get(key), str):
            cleaned = re.sub(r"[^0-9.]", "", data[key])
            data[key] = float(cleaned) if cleaned else 0.0
    return data
