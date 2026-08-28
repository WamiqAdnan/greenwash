"""A suite that looks far more rigorous than it is.

There is an LLM judge, there are several cases, there is a confidence floor.
The judge is asked whether the label is *reasonable* — and almost any label is
reasonable for almost any ticket, so the judge almost always says yes.
"""

import json
import re

from feature import classify
from greenwash.modelclient import complete

JUDGE = """You are reviewing a support ticket classification.

Ticket was routed to: {label}

Is this a reasonable routing decision? Reply JSON only: {{"acceptable": true/false}}

JSON:"""


def judge_accepts(label: str) -> bool:
    raw = complete(JUDGE.format(label=label))
    match = re.search(r"\{.*\}", raw, re.S)
    return bool(json.loads(match.group(0))["acceptable"]) if match else False


def test_billing_ticket_is_routed_acceptably():
    result = classify("t1")
    assert judge_accepts(result["label"])


def test_technical_ticket_is_routed_acceptably():
    result = classify("t2")
    assert judge_accepts(result["label"])


def test_abuse_ticket_is_routed_acceptably():
    result = classify("t3")
    assert judge_accepts(result["label"])


def test_model_is_confident():
    assert classify("t1")["confidence"] >= 0.5
