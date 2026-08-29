# Trajectory — auditor-v1 on 04_purchase_orders

- model: `qwen3:8b` (replay mode)
- tools: `read_feature`, `read_suite`, `list_operators`, `observe`, `run_operator`, `propose_closing_test`
- closing-test attempts allowed per survivor: 3
- operator budget: none (whole applicable catalogue)

## The agent's instructions

```
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.
```


## Phase 1 — triage: read the case, order the sabotages, record a prior

**2. tool call** `read_feature(case='04_purchase_orders')`

**3. read_feature responded**

```
"""Purchase order extraction — the feature under test.

Identical in shape to `01_invoice_extractor`. The difference is entirely in the
suite: this is the Corpus Case that is supposed to come out clean.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), po_number (string), date (YYYY-MM-DD string),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Read the purchase order below and return JSON only, containing:
vendor (string, exactly as written), po_number (string), date (string in YYYY-MM-DD form),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction asking for one more field — see `schema.add_field`. Both
# sample purchase orders print the vendor's address under its name, so this is a
# field the documents really carry. Nothing that was already returned changes.
PROMPT_EXTRA_FIELD = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), vendor_address (string), po_number (string),
date (YYYY-MM-DD string), currency (3-letter code string), subtotal (number),
tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


def read_po(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the purchase order's fields as a dict."""
    raw = complete(PROMPT.format(text=read_po(name)))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    for key in ("subtotal", "tax", "total"):
        if isinstance(data.get(key), str):
            cleaned = re.sub(r"[^0-9.]", "", data[key])
            data[key] = float(cleaned) if cleaned else 0.0
    return data
```

**4. tool call** `read_suite(case='04_purchase_orders')`

**5. read_suite responded**

```
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
```

**6. tool call** `list_operators(tags=['amounts', 'extraction', 'llm', 'structured_output'])`

**7. list_operators responded**

```
- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `value.zero_amounts` — Every monetary amount comes back as zero.
- `value.null_fields` — Every extracted field is present but null.
- `value.transpose_digits` — Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.
- `schema.drop_field` — One field silently disappears from the structured output.
```

**8. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run on the clean feature, where it must pass;
under the sabotage, where it must fail; and under any change that does not break
the feature at all, where it must pass again. If it does not do all of that, you
are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Purchase order extraction — the feature under test.

Identical in shape to `01_invoice_extractor`. The difference is entirely in the
suite: this is the Corpus Case that is supposed to come out clean.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), po_number (string), date (YYYY-MM-DD string),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Read the purchase order below and return JSON only, containing:
vendor (string, exactly as written), po_number (string), date (string in YYYY-MM-DD form),
currency (3-letter code string), subtotal (number), tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


# The same instruction asking for one more field — see `schema.add_field`. Both
# sample purchase orders print the vendor's address under its name, so this is a
# field the documents really carry. Nothing that was already returned changes.
PROMPT_EXTRA_FIELD = """Extract these fields from the purchase order below and reply with JSON only:
vendor (string, exactly as written), vendor_address (string), po_number (string),
date (YYYY-MM-DD string), currency (3-letter code string), subtotal (number),
tax (number), total (number),
line_items (list of objects with description, quantity, unit_price, line_total).

Purchase order:
{text}

JSON:"""


def read_po(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the purchase order's fields as a dict."""
    raw = complete(PROMPT.format(text=read_po(name)))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    for key in ("subtotal", "tax", "total"):
        if isinstance(data.get(key), str):
            cleaned = re.sub(r"[^0-9.]", "", data[key])
            data[key] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that guards it

```python
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

```

## The sabotages available for this feature

- `model.downgrade` — The model behind the feature is swapped for a much weaker one.
- `model.echo` — The model is replaced by one that echoes its input back.
- `value.zero_amounts` — Every monetary amount comes back as zero.
- `value.null_fields` — Every extracted field is present but null.
- `value.transpose_digits` — Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.
- `schema.drop_field` — One field silently disappears from the structured output.

## Your task

Order the sabotages, most likely to slip past this suite first. Then say which
you expect it to miss. You will find out; this is recorded so we can compare
what you expected with what actually happened.

Reply with JSON only:

{"order": ["sabotage.id", ...], "expect_missed": ["sabotage.id", ...], "why": "one sentence"}

JSON:
````

</details>

**9. `qwen3:8b` answered**

```
{"order": ["value.null_fields", "value.zero_amounts", "schema.drop_field", "value.transpose_digits", "model.downgrade"], "expect_missed": ["schema.drop_field"], "why": "The suite checks for presence of fields but does not verify that all required fields are present, making it blind to silently dropped fields."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "value.null_fields",
    "value.zero_amounts",
    "schema.drop_field",
    "value.transpose_digits",
    "model.downgrade"
  ],
  "expect_missed": [
    "schema.drop_field"
  ],
  "why": "The suite checks for presence of fields but does not verify that all required fields are present, making it blind to silently dropped fields.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='value.null_fields')`

**12. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
=======
FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
FAILED tests/test_feature.py::test_the_date_is_a_date_and_the_currency_is_a_real_code
FAILED tests/test_feature.py::test_each_line_total_is_the_quantity_times_the_unit_price
FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - Ty...
FAILED tests/test_feature.py::test_the_totals_reconcile - TypeError: unsuppor...
FAILED tests/test_feature.py::test_the_document_facts_come_back_correctly - A...
FAILED tests/test_feature.py::test_what_it_returned_is_actually_in_the_document
7 failed in N.NNs
```

**13. tool call** `run_operator(operator='value.zero_amounts')`

**14. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - As...
    result = extract(sample)
            assert result["po_number"] == facts["po_number"]
            assert result["date"] == facts["date"]
>           assert abs(result["total"] - facts["total"]) < 0.01
E           assert 6982.5 < 0.01
E            +  where 6982.5 = abs((0 - 6982.5))

tests/test_feature.py:71: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - As...
FAILED tests/test_feature.py::test_the_document_facts_come_back_correctly - a...
2 failed, 5 passed in N.NNs
```

**15. tool call** `run_operator(operator='schema.drop_field')`

**16. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
"The check case 03's suite is missing: is the answer grounded in the source?"""
        for sample in SAMPLES:
            source = read_po(sample)
            result = extract(sample)
>           assert result["vendor"] in source
                   ^^^^^^^^^^^^^^^^
E           KeyError: 'vendor'

tests/test_feature.py:79: KeyError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
FAILED tests/test_feature.py::test_what_it_returned_is_actually_in_the_document
2 failed, 5 passed in N.NNs
```

**17. tool call** `run_operator(operator='value.transpose_digits')`

**18. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - As...
"po_number"]
            assert result["date"] == facts["date"]
>           assert abs(result["total"] - facts["total"]) < 0.01
E           assert 90.0 < 0.01
E            +  where 90.0 = abs((6892.5 - 6982.5))

tests/test_feature.py:71: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - As...
FAILED tests/test_feature.py::test_the_totals_reconcile - assert 9.0 < 0.01
FAILED tests/test_feature.py::test_the_document_facts_come_back_correctly - a...
3 failed, 4 passed in N.NNs
```

**19. tool call** `run_operator(operator='model.downgrade')`

**20. run_operator responded**

```
INERT — the feature returned exactly the same thing
.......                                                                  [100%]
7 passed in N.NNs
```

**21. tool call** `run_operator(operator='model.echo')`

**22. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
=======
FAILED tests/test_feature.py::test_every_field_is_present_and_the_right_type
FAILED tests/test_feature.py::test_the_date_is_a_date_and_the_currency_is_a_real_code
FAILED tests/test_feature.py::test_each_line_total_is_the_quantity_times_the_unit_price
FAILED tests/test_feature.py::test_the_line_items_add_up_to_the_subtotal - Va...
FAILED tests/test_feature.py::test_the_totals_reconcile - ValueError: model d...
FAILED tests/test_feature.py::test_the_document_facts_come_back_correctly - V...
FAILED tests/test_feature.py::test_what_it_returned_is_actually_in_the_document
7 failed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**23. tool call** `observe(operator=None)`

**24. observe responded**

```
call 1: lambda: feature.extract("po_1.txt")
  returned {"currency": "AED", "date": "2026-03-14", "line_items": [{"description": "Standing desk, electric", "line_total": 5800.0, "quantity": 4, "unit_price": 1450.0}, {"description": "Desk mat, felt", "line_total": 850.0, "quantity": 10, "unit_price": 85.0}], "po_number": "PO-2026-1180", "subtotal": 6650.0, "tax": 332.5, "total": 6982.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("po_2.txt")
  returned {"currency": "AED", "date": "2026-04-02", "line_items": [{"description": "A4 paper, box of 5 reams", "line_total": 504.0, "quantity": 12, "unit_price": 42.0}, {"description": "Whiteboard markers, pack of 8", "line_total": 117.0, "quantity": 6, "unit_price": 19.5}], "po_number": "PO-2026-0447", "subtotal": 621.0, "tax": 31.05, "total": 652.05, "vendor": "AL RAYYAN OFFICE SUPPLIES"}
```


## Phase 4 — report

**25. result**

```json
{
  "survivors": [],
  "closed": [],
  "kill_rate_before": 1.0
}
```

