"""The Operator library — the ways an AI feature breaks quietly.

Classic mutation testing flips `>` into `>=`. That finds nothing here, because
the interesting failures of an LLM feature are not arithmetic. They are: the
model got worse and nobody noticed; the retrieved context was wrong but the
answer still read well; the citation pointed at the wrong page; the judge was
lenient enough to pass anything.

Every Operator is a deliberate, reversible sabotage of a Corpus Case, applied
by that case's conftest before its suite runs. An Operator carries `tags`; the
Harness only applies Operators whose tags the case declares, so a retrieval
mutation is never charged against a feature that does no retrieval.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Callable

# A Patch receives the loaded feature module and mutates it in place.
Patch = Callable[[object], None]


@dataclass(frozen=True)
class Operator:
    id: str
    summary: str          # what a reviewer reads in the Trust Report
    tags: tuple[str, ...]  # capability tags a Corpus Case must declare
    patch: Patch = field(repr=False)


REGISTRY: dict[str, Operator] = {}


def operator(id: str, summary: str, tags: tuple[str, ...]):
    def register(fn: Patch) -> Patch:
        REGISTRY[id] = Operator(id=id, summary=summary, tags=tags, patch=fn)
        return fn
    return register


def applicable(tags: set[str]) -> list[Operator]:
    """Operators whose every tag the case declares."""
    return [op for op in REGISTRY.values() if set(op.tags) <= tags]


def get(op_id: str) -> Operator:
    if op_id not in REGISTRY:
        raise KeyError(f"Unknown operator {op_id!r}. Known: {sorted(REGISTRY)}")
    return REGISTRY[op_id]


# ---------------------------------------------------------------------------
# Model quality
# ---------------------------------------------------------------------------

@operator(
    "model.downgrade",
    "The model behind the feature is swapped for a much weaker one.",
    ("llm",),
)
def _downgrade(module) -> None:
    os.environ["GREENWASH_MODEL"] = os.environ.get(
        "GREENWASH_WEAK_MODEL", "qwen3:0.6b"
    )


@operator(
    "model.echo",
    "The model is replaced by one that echoes its input back.",
    ("llm",),
)
def _echo(module) -> None:
    module.complete = lambda prompt, model=None: prompt[-200:]


# ---------------------------------------------------------------------------
# Extracted values
# ---------------------------------------------------------------------------

@operator(
    "value.zero_amounts",
    "Every monetary amount comes back as zero.",
    ("extraction", "amounts"),
)
def _zero_amounts(module) -> None:
    inner = module.extract

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        for k, v in list(result.items()):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                result[k] = 0
        return result

    module.extract = mutated


@operator(
    "value.null_fields",
    "Every extracted field is present but null.",
    ("extraction",),
)
def _null_fields(module) -> None:
    inner = module.extract

    def mutated(*a, **kw):
        return {k: None for k in inner(*a, **kw)}

    module.extract = mutated


@operator(
    "value.transpose_digits",
    "Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.",
    ("extraction", "amounts"),
)
def _transpose(module) -> None:
    inner = module.extract

    def swap(x):
        s = str(x)
        digits = [i for i, c in enumerate(s) if c.isdigit()]
        if len(digits) < 2:
            return x
        i, j = digits[1], digits[2] if len(digits) > 2 else digits[0]
        chars = list(s)
        chars[i], chars[j] = chars[j], chars[i]
        try:
            return type(x)("".join(chars))
        except Exception:
            return x

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        for k, v in list(result.items()):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                result[k] = swap(v)
        return result

    module.extract = mutated


# ---------------------------------------------------------------------------
# Citations and provenance
# ---------------------------------------------------------------------------

@operator(
    "citation.wrong_page",
    "Every citation points at a real but wrong location in the source.",
    ("citations",),
)
def _wrong_page(module) -> None:
    inner = module.answer

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        for c in result.get("citations", []):
            c["page"] = c.get("page", 1) + 1
        return result

    module.answer = mutated


@operator(
    "citation.fabricate",
    "Citations are invented: plausible quotes that appear nowhere in the source.",
    ("citations",),
)
def _fabricate(module) -> None:
    inner = module.answer

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        for c in result.get("citations", []):
            c["quote"] = "as set out in the preceding paragraph"
        return result

    module.answer = mutated


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@operator(
    "retrieval.truncate",
    "Only the first half of the retrieved context reaches the model.",
    ("retrieval",),
)
def _truncate(module) -> None:
    inner = module.retrieve

    def mutated(*a, **kw):
        chunks = inner(*a, **kw)
        return chunks[: max(1, len(chunks) // 2)]

    module.retrieve = mutated


@operator(
    "retrieval.shuffle",
    "Retrieved chunks arrive in a scrambled order.",
    ("retrieval",),
)
def _shuffle(module) -> None:
    inner = module.retrieve

    def mutated(*a, **kw):
        chunks = list(inner(*a, **kw))
        random.Random(0).shuffle(chunks)
        return chunks

    module.retrieve = mutated


# ---------------------------------------------------------------------------
# Classification and judging
# ---------------------------------------------------------------------------

@operator(
    "classify.collapse",
    "Every input is classified into the single most common label.",
    ("classification",),
)
def _collapse(module) -> None:
    inner = module.classify

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        result["label"] = getattr(module, "MAJORITY_LABEL", "billing")
        return result

    module.classify = mutated


@operator(
    "classify.confidence_pin",
    "Confidence is pinned high regardless of how uncertain the model was.",
    ("classification", "confidence"),
)
def _confidence(module) -> None:
    inner = module.classify

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        result["confidence"] = 0.99
        return result

    module.classify = mutated


@operator(
    "schema.drop_field",
    "One field silently disappears from the structured output.",
    ("structured_output",),
)
def _drop_field(module) -> None:
    inner = module.extract
    victim = os.environ.get("GREENWASH_DROP_FIELD", "")

    def mutated(*a, **kw):
        result = inner(*a, **kw)
        target = victim or (sorted(result)[-1] if result else None)
        result.pop(target, None)
        return result

    module.extract = mutated


def load_ground_truth(path) -> dict:
    """The Blind Spots a Corpus Case is known to have, by Operator id."""
    return json.loads(open(path).read())
