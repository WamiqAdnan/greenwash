"""The control suite: one that would actually notice.

Case 01's suite checks that three keys exist. This one checks the values against
the document they came from, which is the whole difference between a test and a
formality.

Nothing here is exotic and none of it is snapshotting the model's phrasing. Every
assertion is a fact of the purchase order — the arithmetic has to reconcile, the
date has to be a date, the vendor has to be a string that actually appears in the
source. A careful team writes exactly this, and Greenwash should find nothing.
"""

import re

from feature import extract, read_po

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CURRENCIES = {"AED", "USD", "EUR", "GBP", "SAR"}
SAMPLES = ["po_1.txt", "po_2.txt"]

# Facts of the documents, not of the model. Read them off the samples yourself.
DOCUMENT_FACTS = {
    "po_1.txt": {"po_number": "PO-2026-1180", "date": "2026-03-14", "total": 6982.50},
    "po_2.txt": {"po_number": "PO-2026-0447", "date": "2026-04-02", "total": 652.05},
}


def test_every_field_is_present_and_the_right_type():
    for sample in SAMPLES:
        result = extract(sample)
        for field in ("vendor", "po_number", "date", "currency"):
            assert isinstance(result[field], str) and result[field].strip()
        for field in ("subtotal", "tax", "total"):
            assert isinstance(result[field], (int, float))
        assert isinstance(result["line_items"], list) and result["line_items"]


def test_the_date_is_a_date_and_the_currency_is_a_real_code():
    for sample in SAMPLES:
        result = extract(sample)
        assert ISO_DATE.match(result["date"]), result["date"]
        assert result["currency"] in CURRENCIES, result["currency"]


def test_each_line_total_is_the_quantity_times_the_unit_price():
    for sample in SAMPLES:
        for item in extract(sample)["line_items"]:
            expected = item["quantity"] * item["unit_price"]
            assert abs(item["line_total"] - expected) < 0.01, item


def test_the_line_items_add_up_to_the_subtotal():
    for sample in SAMPLES:
        result = extract(sample)
        summed = sum(item["line_total"] for item in result["line_items"])
        assert abs(summed - result["subtotal"]) < 0.01, (summed, result["subtotal"])


def test_the_totals_reconcile():
    for sample in SAMPLES:
        result = extract(sample)
        assert abs(result["subtotal"] + result["tax"] - result["total"]) < 0.01
        assert abs(result["tax"] - result["subtotal"] * 0.05) < 0.01


def test_the_document_facts_come_back_correctly():
    for sample, facts in DOCUMENT_FACTS.items():
        result = extract(sample)
        assert result["po_number"] == facts["po_number"]
        assert result["date"] == facts["date"]
        assert abs(result["total"] - facts["total"]) < 0.01


def test_what_it_returned_is_actually_in_the_document():
    """The check case 03's suite is missing: is the answer grounded in the source?"""
    for sample in SAMPLES:
        source = read_po(sample)
        result = extract(sample)
        assert result["vendor"] in source
        assert result["po_number"] in source
        for item in result["line_items"]:
            assert item["description"] in source, item["description"]
