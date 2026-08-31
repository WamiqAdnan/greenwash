"""A Benign Change must never be able to reach the Kill Rate.

The two registries are the same shape and are applied by the same conftest line,
so nothing but this separation stops a reworded prompt being scored as a
sabotage — at which case 03, where the suite stays green under it, would be
reported as a Blind Spot that does not exist.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness, observe, operators as ops  # noqa: E402

CASE = harness.Case(ROOT / "corpus" / "03_rag_citations")


def test_benign_changes_are_not_in_the_sabotage_catalogue():
    sabotages = {op.id for op in ops.REGISTRY.values()}
    assert not (sabotages & set(ops.BENIGN)), "an id is registered as both"


def test_the_kill_rate_sweep_never_sees_a_benign_change():
    for case in harness.discover():
        applied = {op.id for op in case.operators()}
        assert not (applied & set(ops.BENIGN))


def test_a_case_can_still_apply_one_by_id():
    """The conftest resolves through `get`, which sees both registries."""
    assert ops.get("prompt.reword").id == "prompt.reword"


def test_rewording_the_prompt_changes_what_the_feature_says_but_not_what_it_means():
    """The premise of the brittleness probe, as a test.

    If this ever goes inert the probe measures nothing, and it should say so
    rather than report a clean bill of health.
    """
    clean = observe.observe(CASE.path)
    reworded = observe.observe(CASE.path, "prompt.reword")
    assert not observe.failed(reworded)
    assert clean != reworded, "no variation — the probe would measure nothing"
    for before, after in zip(clean, reworded):
        assert "2.5 days" in before["returned"] or "10 days" in before["returned"]
        assert "2.5 days" in after["returned"] or "10 days" in after["returned"]


def test_the_case_s_own_suite_stays_green_under_a_benign_change():
    """It is only benign if the feature still works."""
    green, _out = CASE.run_suite("prompt.reword")
    assert green


# --- holding one back from the Gate -----------------------------------------

def test_at_least_one_benign_change_is_held_out_of_the_gate():
    """The invariant that makes `evals/brittleness.py` worth running.

    The Gate rejects a Closing Test that goes red under a Benign Change. If the
    probe then applies only the same changes, it is grading the Gate's own
    homework: zero False Alarms is guaranteed and says nothing about the tests.
    Something has to be held back, or the number is decoration.
    """
    assert ops.HELD_OUT, (
        "no Held-Out Benign Change — brittleness.py can only confirm the "
        "gate's own rule"
    )
    assert ops.HELD_OUT <= set(ops.BENIGN), "held out, but not registered"


def test_the_gate_never_applies_a_held_out_benign_change():
    for case in harness.discover():
        gated = {op.id for op in ops.applicable_benign(case.tags, include_held_out=False)}
        assert not (gated & ops.HELD_OUT), f"{case.name} would let the gate see one"


def test_the_probe_still_sees_every_benign_change():
    """Held out of the Gate, not out of the measurement — that is the point."""
    for case in harness.discover():
        everything = {op.id for op in ops.applicable_benign(case.tags)}
        gated = {op.id for op in ops.applicable_benign(case.tags, include_held_out=False)}
        assert gated <= everything
        assert everything - gated == ops.HELD_OUT & everything


def test_a_case_missing_its_variant_is_a_harness_fault_not_a_detection():
    """The trap a new Corpus Case walks into, closed.

    A Benign Change that swaps in an alternative prompt cannot be applied to a
    case that never declared one. That used to raise a bare `AttributeError`,
    which is not a `HARNESS_FAULTS` signature, so the suite went red for a
    machinery reason that reads exactly like a real detection. `MissingVariant`
    is in the list; `AttributeError` deliberately is not, because a Feature can
    raise one for real and a Kill thrown away as Invalid is the same bug facing
    the other way.
    """
    class Bare:
        __name__ = "feature"

    for change in ("prompt.reword", "schema.add_field", "schema.add_confidence"):
        try:
            ops.get(change).patch(Bare())
        except ops.MissingVariant as exc:
            assert any(f in f"{type(exc).__name__}: {exc}" for f in harness.HARNESS_FAULTS)
        else:
            raise AssertionError(f"{change} accepted a case with no variant")

    assert "AttributeError" not in harness.HARNESS_FAULTS
