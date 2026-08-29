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


class MissingVariant(RuntimeError):
    """A Corpus Case did not declare the alternative prompt a Benign Change needs.

    Its own signature rather than a bare `AttributeError`, and listed in
    `HARNESS_FAULTS`, because the two are indistinguishable from outside: a case
    added without `PROMPT_VARIANT` goes red for a machinery reason that reads
    exactly like a real detection. Adding `AttributeError` to that list instead
    would be worse — a Feature can raise one for real, and then a Kill would be
    thrown away as Invalid.
    """


@dataclass(frozen=True)
class Operator:
    id: str
    summary: str          # what a reviewer reads in the Trust Report
    tags: tuple[str, ...]  # capability tags a Corpus Case must declare
    patch: Patch = field(repr=False)


REGISTRY: dict[str, Operator] = {}

# The other half of the library. A Benign Change is a change a team really makes
# — reword the prompt, move the model — that does **not** break the Feature. The
# Suite is supposed to stay green under one. A test that goes red is a False
# Alarm, and false alarms are how a tool like this loses its user.
#
# Deliberately a separate registry: `applicable()` must never hand one of these
# to the Kill Rate sweep, where "the suite stayed green" would be scored as a
# Blind Spot. `get()` sees both, so a Corpus Case's conftest needs no changes.
BENIGN: dict[str, Operator] = {}

# Benign Changes the Verification Gate is not allowed to apply, reserved for
# `evals/brittleness.py`. Once the Gate started rejecting Closing Tests that go
# red under a Benign Change, the probe that counts False Alarms was measuring
# the Gate's own rule: same change, same runs, so zero was guaranteed and meant
# only that the Gate had executed. Holding one back is what makes that number a
# second opinion again.
#
# This is a statement about the experiment rather than about the change. Moving
# `model.swap` inside the Gate is deleting one keyword — and the day there are
# several Benign Changes, whichever is held out should be the one whose False
# Alarms you would most regret shipping.
HELD_OUT: set[str] = set()


def operator(id: str, summary: str, tags: tuple[str, ...]):
    def register(fn: Patch) -> Patch:
        REGISTRY[id] = Operator(id=id, summary=summary, tags=tags, patch=fn)
        return fn
    return register


def benign(id: str, summary: str, tags: tuple[str, ...], held_out: bool = False):
    def register(fn: Patch) -> Patch:
        BENIGN[id] = Operator(id=id, summary=summary, tags=tags, patch=fn)
        if held_out:
            HELD_OUT.add(id)
        return fn
    return register


def applicable(tags: set[str]) -> list[Operator]:
    """Operators whose every tag the case declares. Sabotages only."""
    return [op for op in REGISTRY.values() if set(op.tags) <= tags]


def applicable_benign(tags: set[str], *, include_held_out: bool = True) -> list[Operator]:
    """Benign Changes this Corpus Case declares the tags for.

    Everything gets them all — the brittleness probe, which is what a Held-Out
    Benign Change exists for, and `record_fixtures.py`, which has to record a
    pass for every change that rewrites a prompt whether the Gate applies it or
    not. Only the Gate passes `include_held_out=False`.
    """
    return [
        op for op in BENIGN.values()
        if set(op.tags) <= tags and (include_held_out or op.id not in HELD_OUT)
    ]


def get(op_id: str) -> Operator:
    if op_id in REGISTRY:
        return REGISTRY[op_id]
    if op_id in BENIGN:
        return BENIGN[op_id]
    raise KeyError(
        f"Unknown operator {op_id!r}. Known: {sorted(REGISTRY)} "
        f"and benign: {sorted(BENIGN)}"
    )


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


# ---------------------------------------------------------------------------
# Benign Changes — the things that are *not* breakages
# ---------------------------------------------------------------------------

@benign(
    "schema.add_field",
    "The feature is asked for one more field than it used to return.",
    ("extraction",),
)
def _add_field(module) -> None:
    """Ask the same extraction for one extra field the document already carries.

    The Benign Change the other two cannot make. Rewording a prompt and swapping
    a model both leave an extraction Feature returning byte-identical JSON — the
    invoice says what it says — so the Verification Gate had nothing to hold a
    Closing Test on `01` or `04` to. Widening the schema is the one ordinary
    change that does move that output, and it is the change those teams make
    most: somebody wants one more column.

    Benign in the exact sense that matters. Every field that was there before is
    still there and still right; the dict simply has one more key. A Closing Test
    that asserts a value is untouched. One that pins the whole dict, or the set
    of keys, goes red — and should.
    """
    _swap_prompt(module, "PROMPT_EXTRA_FIELD")


@benign(
    "model.swap",
    "The model behind the feature is swapped for a different one of comparable "
    "quality.",
    ("llm",),
    held_out=True,
)
def _swap(module) -> None:
    """Move the Feature onto another vendor's model of the same class.

    The most ordinary change there is — a team switches models roughly whenever
    a new one lands — and the one a snapshot test cannot survive, because two
    models never word an answer the same way. `qwen3:8b` to `llama3.1:8b` is
    deliberately a sideways move and not a better model: "better" is a claim
    that would need a benchmark behind it, and nothing here rests on the new
    model being stronger, only on it still being right. That it still is, is
    checked by hand and by the Corpus Case's own suite staying green.

    Held out of the Verification Gate on purpose — see `HELD_OUT`.
    """
    os.environ["GREENWASH_MODEL"] = os.environ.get(
        "GREENWASH_OTHER_MODEL", "llama3.1:8b"
    )


@benign(
    "prompt.reword",
    "The prompt is reworded to say the same thing differently.",
    ("llm",),
)
def _reword(module) -> None:
    """Swap in the equivalent prompt the Corpus Case declares.

    Hand-written per case and read by a human, because "means the same thing"
    is not something to leave to a regex. Changing the prompt changes the
    Fixture key, so a case needs its own recording pass for this — exactly like
    the `retrieval.*` Operators.
    """
    _swap_prompt(module, "PROMPT_VARIANT")


def _swap_prompt(module, attribute: str) -> None:
    """Point the Feature at one of the alternative prompts its case declares."""
    variant = getattr(module, attribute, None)
    if variant is None:
        raise MissingVariant(
            f"{module.__name__} declares no {attribute}, so this benign change "
            f"cannot be applied. Add one, or drop the tag that selects it."
        )
    module.PROMPT = variant


def load_ground_truth(path) -> dict:
    """The Blind Spots a Corpus Case is known to have, by Operator id."""
    return json.loads(open(path).read())
