"""Every Operator, applied to every case that declares its tags, actually runs.

This test exists because the failure it catches happened, twice, in this
project's own history — and the second time it was in these very Operators.

`greenwash/operators.py` did not import `re`. Three new Operators used it, so
each one raised `NameError` the moment it was applied. The Feature blew up, the
Suite went red, and `run_eval` scored all three as **Kills**: two Corpus Cases
briefly reported a Kill Rate of 100% and 75% on the strength of our own bug.
`NameError` is not a `HARNESS_FAULTS` signature and should not become one — a
Feature can raise one for real, and a Kill discarded as Invalid is the same
mistake facing the other way.

So the guard belongs here instead. An Operator that cannot be applied at all is
never a measurement, whatever colour the suite comes out.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness, observe, operators as ops  # noqa: E402

# Signatures of the Operator itself being broken, as opposed to the Feature
# failing because it was successfully sabotaged — which is the point.
BROKEN_OPERATOR = (
    "NameError",
    "ImportError",
    "ModuleNotFoundError",
    "MissingVariant",
    "TypeError: 'NoneType'",
)

CASES = harness.discover()
PAIRS = [
    (case, op)
    for case in CASES
    for op in case.operators() + ops.applicable_benign(case.tags)
]


@pytest.mark.parametrize(
    "case,op", PAIRS, ids=[f"{c.name}:{o.id}" for c, o in PAIRS]
)
def test_the_operator_can_actually_be_applied(case, op):
    observations = observe.observe(case.path, op.id)
    assert not observe.failed(observations), (
        f"{op.id} could not be applied to {case.name} at all:\n"
        f"{observations[0].get('raised', '')}"
    )
    for record in observations:
        raised = record.get("raised", "")
        for signature in BROKEN_OPERATOR:
            assert signature not in raised, (
                f"{op.id} on {case.name} raised {raised!r} — that is the "
                f"operator being broken, not the feature being sabotaged, and "
                f"a red suite here would be scored as a kill"
            )
