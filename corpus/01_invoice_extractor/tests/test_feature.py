"""The suite a real team wrote, and the reason they trust the feature.

Nothing here is a strawman. Every assertion is one people write.
"""

from feature import extract


def test_extraction_returns_a_result():
    result = extract("invoice_1.txt")
    assert result is not None


def test_extraction_has_the_expected_fields():
    result = extract("invoice_1.txt")
    assert "vendor" in result
    assert "invoice_number" in result
    assert "total" in result
