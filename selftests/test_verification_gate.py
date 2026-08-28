"""The Gate is the product's one constraint, so it gets the first test.

A Closing Test may only be reported if it is green on the clean Feature and red
under the Mutant it claims to close. Everything else the Auditor does is
convenience; this is what makes its output worth reading.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auditor.agent import VerificationGate  # noqa: E402
from greenwash import harness  # noqa: E402

CASE = harness.Case(ROOT / "corpus" / "01_invoice_extractor")
OPERATOR = "value.zero_amounts"

# What the suite already does, and the reason the Mutant survived it.
TOOTHLESS = '''
from feature import extract


def test_extraction_returns_a_result_again():
    assert extract("invoice_1.txt") is not None
'''

# Asserts on a value, which is the whole difference.
REAL = '''
from feature import extract


def test_total_is_not_zero():
    assert extract("invoice_1.txt")["total"] > 0
'''

# Green under neither: there is no such sample, so it errors before asserting.
BROKEN = '''
from feature import extract


def test_total_on_a_sample_that_does_not_exist():
    assert extract("invoice_9.txt")["total"] > 0
'''


def gate(tmp_path):
    return VerificationGate(CASE, scratch=tmp_path)


def test_a_test_that_passes_under_the_mutant_is_rejected(tmp_path):
    verdict = gate(tmp_path).judge(OPERATOR, TOOTHLESS)
    assert not verdict.accepted
    assert verdict.clean_green
    assert not verdict.kills_mutant
    assert "still passed" in verdict.reason


def test_a_test_that_asserts_on_the_value_is_accepted(tmp_path):
    verdict = gate(tmp_path).judge(OPERATOR, REAL)
    assert verdict.accepted, verdict.reason
    assert verdict.clean_green and verdict.kills_mutant
    assert "test_total_is_not_zero" in verdict.failure_line


def test_a_test_that_is_red_on_the_clean_feature_is_rejected(tmp_path):
    verdict = gate(tmp_path).judge(OPERATOR, BROKEN)
    assert not verdict.accepted
    assert not verdict.clean_green
    assert "clean" in verdict.reason


def test_the_gate_never_touches_the_real_case(tmp_path):
    before = sorted(p.name for p in (CASE.path / "tests").iterdir() if p.is_file())
    gate(tmp_path).judge(OPERATOR, REAL)
    after = sorted(p.name for p in (CASE.path / "tests").iterdir() if p.is_file())
    assert before == after


# --- the Inert state --------------------------------------------------------

CONTROL = harness.Case(ROOT / "corpus" / "04_purchase_orders")


def test_a_sabotage_that_changes_nothing_is_inert_not_a_survivor():
    """The precision control's whole job, as a test.

    `qwen3:0.6b` extracts these purchase orders byte-identically to `qwen3:8b`,
    so `model.downgrade` leaves a green suite with nothing to catch. Reporting
    that as a Blind Spot is the false alarm that costs the user their trust.
    """
    op = next(o for o in CONTROL.operators() if o.id == "model.downgrade")
    result, _out, _clean = harness.evaluate_mutant(CONTROL, op)
    assert result.inert
    assert result.status == "INERT"
    assert not result.killed


def test_inert_mutants_leave_the_kill_rate_alone():
    result = harness.run_case(CONTROL)
    assert result.inert == ["model.downgrade"]
    assert "model.downgrade" not in result.survivors
    assert result.kill_rate == 1.0, "every sabotage that did anything was caught"
