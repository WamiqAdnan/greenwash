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
