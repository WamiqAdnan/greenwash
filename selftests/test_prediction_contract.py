"""The Auditor must be measurable by the same scorer as the Baseline.

One scorer, one ground truth, no post-hoc metric changes — that is what keeps
the headline comparison honest, and it is the first thing a reviewer will check.
So the contract is a test rather than a convention.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from greenwash import harness, operators as ops  # noqa: E402

AUDITOR = ROOT / "auditor" / "predictions.json"
BASELINE = ROOT / "baseline" / "predictions.json"


def _scorer():
    """Load the shared scorer from its path — `evals/` is scripts, not a package."""
    spec = importlib.util.spec_from_file_location(
        "score_predictions", ROOT / "evals" / "score_predictions.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _overall(doc) -> tuple[float, float, float]:
    predicted, truth = set(), set()
    cases = {c.name: c for c in harness.discover()}
    for name, ids in doc["predictions"].items():
        predicted |= {f"{name}:{i}" for i in ids}
        truth |= {f"{name}:{i}" for i in cases[name].known_blind_spots}
    return _scorer().prf(predicted, truth)


@pytest.fixture(scope="module")
def audit():
    if not AUDITOR.exists():
        pytest.skip("no audit yet — run auditor/audit.py")
    return json.loads(AUDITOR.read_text())


def test_it_answers_in_the_shape_the_scorer_reads(audit):
    assert audit["predictor"] == "auditor-v1"
    assert audit["model"]
    assert audit["verified"] is True, "the auditor's whole claim is that it ran things"
    assert isinstance(audit["predictions"], dict)


def test_it_covers_every_corpus_case(audit):
    assert set(audit["predictions"]) == {c.name for c in harness.discover()}


def test_every_reported_id_is_a_real_operator_the_case_can_run(audit):
    for name, ids in audit["predictions"].items():
        case = next(c for c in harness.discover() if c.name == name)
        applicable = {op.id for op in case.operators()}
        for op_id in ids:
            assert op_id in ops.REGISTRY, f"{name}: {op_id} is not an operator"
            assert op_id in applicable, f"{name}: {op_id} does not apply to this case"


def test_it_invents_nothing(audit):
    assert all(not v for v in audit.get("hallucinated_ids", {}).values())


def test_it_beats_the_baseline_on_the_shared_scorer(audit):
    baseline = json.loads(BASELINE.read_text())
    _, _, baseline_f1 = _overall(baseline)
    _, _, auditor_f1 = _overall(audit)
    assert auditor_f1 > baseline_f1, (
        f"auditor f1 {auditor_f1:.2f} vs baseline {baseline_f1:.2f}"
    )


def test_every_closed_blind_spot_was_reported_as_one(audit):
    """Closing a hole nobody found is a bookkeeping bug, and it would flatter us."""
    for name, closed in audit.get("closed", {}).items():
        assert set(closed) <= set(audit["predictions"][name])
