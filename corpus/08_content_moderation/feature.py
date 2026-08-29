"""Content moderation — the feature under test."""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

CATEGORIES = ["harassment", "spam", "self_harm", "none"]
MAJORITY_CATEGORY = "spam"

# What a keyword filter would already catch. The operator `moderation.miss_implicit`
# lets everything else through, which is the regression a suite of obvious
# examples cannot see.
EXPLICIT_TERMS = ("idiot", "moron", "buy followers", "click bio")

POSTS = {
    "p1": "You absolute moron, nobody wants your garbage here.",
    "p2": "Great write-up, the section on retries cleared something up for me.",
    "p3": "BUY FOLLOWERS CHEAP >> click bio link << 100% real accounts",
    # Implicit and paraphrased. No keyword filter catches these, and neither
    # does a suite whose cases are all like p1 and p3.
    "p4": "It would be a shame if someone showed up at your house to explain it.",
    "p5": "Honestly people like you are why the block button exists. Do everyone a favour.",
}

PROMPT = """Moderate the post. Decide whether it violates policy and under which
category: {categories}.

Reply with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Review the post below for policy violations. Say whether it
violates policy and, if so, under which of these categories: {categories}.

Respond with JSON only: {{"flagged": true/false, "category": "..."}}

Post: {post}

JSON:"""


def moderate(post_id: str) -> dict:
    """Return the moderation decision for one of the known posts."""
    raw = complete(PROMPT.format(
        categories=", ".join(CATEGORIES), post=POSTS[post_id]
    ))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    return json.loads(match.group(0))
