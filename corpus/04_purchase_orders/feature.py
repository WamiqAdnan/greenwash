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
