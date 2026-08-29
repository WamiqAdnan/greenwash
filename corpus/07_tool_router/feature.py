"""Tool routing — the feature under test.

Picks the tool for a support request and fills in its arguments. The arguments
are the part that moves money.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

TOOLS = [
    {"name": "issue_refund", "arguments": ["order_id", "amount"]},
    {"name": "update_address", "arguments": ["customer_id", "new_address"]},
    {"name": "escalate_to_human", "arguments": ["reason"]},
]

REQUESTS = {
    "r1": "Order A-4471 was charged 84.00 twice. Refund the duplicate.",
    "r2": "Customer 90210 has moved to 14 Marina Walk, Dubai. Update their address.",
    "r3": "I want to speak to a manager about my last three deliveries.",
}

PROMPT = """Choose exactly one tool for the request and fill in its arguments.

Tools:
{tools}

Reply with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Pick the single tool that handles the request below and
supply its arguments.

Tools:
{tools}

Respond with JSON only: {{"tool": "...", "arguments": {{...}}}}

Request: {request}

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def route(request_id: str) -> dict:
    """Return the tool call for one of the known requests."""
    raw = complete(PROMPT.format(tools=_catalogue(), request=REQUESTS[request_id]))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    call = json.loads(match.group(0))
    call.setdefault("arguments", {})
    return call
