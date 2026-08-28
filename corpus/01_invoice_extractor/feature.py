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
