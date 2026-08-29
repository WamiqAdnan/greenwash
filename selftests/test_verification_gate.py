"""The Gate is the product's one constraint, so it gets the first test.

A Closing Test may only be reported if it is green on the clean Feature, red
under the Mutant it claims to close, and green again under every Benign Change
that moves the Feature's output. Everything else the Auditor does is
convenience; this is what makes its output worth reading.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auditor.agent import VerificationGate  # noqa: E402
from greenwash import harness, operators as ops  # noqa: E402

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


# --- the Benign Changes, inside the Gate ------------------------------------

RAG = harness.Case(ROOT / "corpus" / "03_rag_citations")

# v1's accepted Closing Test for `model.echo`, recovered from
# `trajectories/audit-03_rag_citations.md`. It is green on the clean feature and
# red under the Mutant, so the two-run Gate accepted it — and it is pinned to the
# exact sentence the model happened to produce, so it goes red the next time
# anybody rewords a prompt. That is the failure this third run exists to catch.
SNAPSHOT = '''
from feature import answer


def test_answer_matches():
    result = answer("How much annual leave accrues each month?")
    assert result["answer"] == (
        "The annual leave accrues at 2.5 days per completed month of service. "
        "This information is found on [page 1]."
    )
'''

# What v1.1a wrote instead: every citation checked against the document it came
# from. It says nothing about how the answer is worded, so the rewording cannot
# touch it. This one must still be accepted.
GROUNDED = '''
from feature import answer

PAGES = {
    1: "Annual leave accrues at 2.5 days per completed month of service.",
    2: "Unused annual leave may be carried over, to a maximum of 10 days.",
    3: "Probation lasts six months. Leave may not be taken during probation.",
    4: "Sick leave requires a medical certificate from the third consecutive day.",
}


def test_citations_have_valid_quotes():
    result = answer("How much annual leave accrues each month?")
    assert all(c["quote"] == PAGES[c["page"]] for c in result["citations"])
'''


def test_a_test_that_pins_the_models_prose_is_rejected(tmp_path):
    """Over-fitting, caught where it happens instead of counted afterwards."""
    verdict = VerificationGate(RAG, scratch=tmp_path).judge("model.echo", SNAPSHOT)
    assert not verdict.accepted
    assert verdict.clean_green and verdict.kills_mutant, (
        "it does everything the two-run gate asked of it"
    )
    assert verdict.false_alarm_under == "prompt.reword"


def test_a_test_that_asserts_the_documents_facts_is_still_accepted(tmp_path):
    verdict = VerificationGate(RAG, scratch=tmp_path).judge(
        "citation.fabricate", GROUNDED
    )
    assert verdict.accepted, verdict.reason
    assert verdict.benign_checked == ("prompt.reword",)


def test_a_harness_fault_under_a_benign_change_is_not_a_false_alarm(tmp_path):
    """The crash-counted-as-a-kill mistake, wearing the other hat.

    If the candidate goes red under a Benign Change because a fixture for the
    reworded prompt is missing, the Gate has learned nothing about the test. It
    says so, and does not reject a test over our own breakage.
    """
    gate_ = VerificationGate(RAG, scratch=tmp_path)
    gate_._benign = ops.applicable_benign(RAG.tags)

    real_run = harness.Case.run_suite

    def flaky(self, operator_id=None, **kw):
        if operator_id == "prompt.reword":
            return False, "E   FixtureMiss: no recorded answer for that prompt"
        return real_run(self, operator_id, **kw)

    harness.Case.run_suite = flaky
    try:
        verdict = gate_.judge("citation.fabricate", GROUNDED)
    finally:
        harness.Case.run_suite = real_run

    assert verdict.accepted, verdict.reason
    assert not verdict.false_alarm_under
    assert verdict.benign_inconclusive == ("prompt.reword",)
    assert "could not be checked" in verdict.reason


def test_an_inert_benign_change_is_not_run_at_all():
    """Each case is held to the Benign Changes that actually move *its* output.

    Running a candidate under a Benign Change that changes nothing is the clean
    run a second time — a wasted subprocess that looks like evidence. So the two
    cases below see different lists, and neither sees a Held-Out change:
    rewording the prompt does not move an extraction feature, and widening the
    schema does not apply to one that answers questions.
    """
    assert [c.id for c in VerificationGate(RAG).observable_benign()] == ["prompt.reword"]
    assert [c.id for c in VerificationGate(CASE).observable_benign()] == ["schema.add_field"]


CLASSIFIER = harness.Case(ROOT / "corpus" / "02_ticket_classifier")

CLASSIFIER_TEST = """
from feature import classify


def test_t2_is_technical():
    assert classify("t2")["label"] == "technical"
"""


def test_a_case_with_no_benign_check_says_so_rather_than_claiming_one(tmp_path):
    """Nothing moves the classifier's output that the Gate is allowed to apply.

    `prompt.reword` is Inert on it and `model.swap` is Held Out, so this Closing
    Test has never been held to one — and the verdict has to say so rather than
    quietly imply a check that did not happen.
    """
    gate_ = VerificationGate(CLASSIFIER, scratch=tmp_path)
    assert gate_.observable_benign() == []
    verdict = gate_.judge("classify.collapse", CLASSIFIER_TEST)
    assert verdict.accepted, verdict.reason
    assert verdict.benign_checked == ()
    assert "no benign change is measurable" in verdict.reason
