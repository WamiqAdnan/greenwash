# Trust Report — 01_invoice_extractor

**The feature.** Extracts vendor, invoice number, date and total from invoice text with a local LLM.

**The suite.** Two tests, both green, both asserting only that the call returned something shaped like a result.

**Kill rate: 33%** — 2 of 6 sabotages were noticed.

4 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

4 of them now have a test that would have caught it.

## `model.downgrade`

The model behind the feature is swapped for a much weaker one.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under model.downgrade
- it fails as: `FAILED tests/test_greenwash_closing.py::test_date_format_consistency - Assert...`
- attempts needed: 1

```python
from feature import extract

def test_date_format_consistency():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["date"] == "2026-03-14"
    assert result2["date"] == "2026-04-02"
```

## `value.zero_amounts`

Every monetary amount comes back as zero.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under value.zero_amounts
- it fails as: `FAILED tests/test_greenwash_closing.py::test_total_amount_not_zero - assert (...`
- attempts needed: 1

```python
from feature import extract

def test_total_amount_not_zero():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] != 0 and result2["total"] != 0
```

## `value.null_fields`

Every extracted field is present but null.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under value.null_fields
- it fails as: `FAILED tests/test_greenwash_closing.py::test_total_is_not_null - assert None ...`
- attempts needed: 1

```python
from feature import extract

def test_total_is_not_null():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] is not None
    assert result2["total"] is not None
```

## `value.transpose_digits`

Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under value.transpose_digits
- it fails as: `FAILED tests/test_greenwash_closing.py::test_total_amount_is_correct - assert...`
- attempts needed: 1

```python
from feature import extract

def test_total_amount_is_correct():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] == 1284.5 and result2["total"] == 375.9
```

## What the auditor expected, before it ran anything

Predicted misses: `value.transpose_digits`

Actually missed: `model.downgrade`, `value.zero_amounts`, `value.null_fields`, `value.transpose_digits`

> The suite lacks tests for numeric precision and field-specific validation, making it blind to subtle data corruption like transposed digits.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
