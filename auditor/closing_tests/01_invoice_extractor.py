"""Closing Tests the Auditor wrote for 01_invoice_extractor.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-01_invoice_extractor.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: value.null_fields — Every extracted field is present but null.
# gate: green on the clean feature, red under value.null_fields, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_total_is_number_not_null - asser...
from feature import extract

def test_total_is_number_not_null():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert isinstance(result1["total"], float)
    assert isinstance(result2["total"], float)


# closes: model.downgrade — The model behind the feature is swapped for a much weaker one.
# gate: green on the clean feature, red under model.downgrade, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_date_format_consistency - Assert...
from feature import extract

def test_date_format_consistency():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["date"] == "2026-03-14"
    assert result2["date"] == "2026-04-02"


# closes: value.zero_amounts — Every monetary amount comes back as zero.
# gate: green on the clean feature, red under value.zero_amounts, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_total_is_non_zero - assert 0 != 0
from feature import extract

def test_total_is_non_zero():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] != 0
    assert result2["total"] != 0


# closes: value.transpose_digits — Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.
# gate: green on the clean feature, red under value.transpose_digits, no benign change is measurable on this feature
# fails as: FAILED tests/test_greenwash_closing.py::test_total_amount_is_correct - assert...
from feature import extract

def test_total_amount_is_correct():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] == 1284.5 and result2["total"] == 375.9
