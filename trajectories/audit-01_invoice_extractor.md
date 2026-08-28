# Trajectory — auditor-v1 on 01_invoice_extractor

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
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.
```


## Phase 1 — triage: read the case, order the sabotages, record a prior

**2. tool call** `read_feature(case='01_invoice_extractor')`

**3. read_feature responded**

```
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data
```

**4. tool call** `read_suite(case='01_invoice_extractor')`

**5. read_suite responded**

```
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
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that guards it

```python
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
{"order": ["model.downgrade", "value.zero_amounts", "value.null_fields", "schema.drop_field", "value.transpose_digits"], "expect_missed": ["value.transpose_digits"], "why": "The suite lacks tests for numeric precision and field-specific validation, making it blind to subtle data corruption like transposed digits."}
```

**10. recorded prior** (evidence, never a finding)

```json
{
  "order": [
    "model.downgrade",
    "value.zero_amounts",
    "value.null_fields",
    "schema.drop_field",
    "value.transpose_digits"
  ],
  "expect_missed": [
    "value.transpose_digits"
  ],
  "why": "The suite lacks tests for numeric precision and field-specific validation, making it blind to subtle data corruption like transposed digits.",
  "invented_ids": []
}
```


## Phase 2 — verify: apply each sabotage, run the suite, read the result

**11. tool call** `run_operator(operator='model.downgrade')`

**12. run_operator responded**

```
SURVIVED — suite stayed green
..                                                                       [100%]
2 passed in N.NNs
```

**13. tool call** `run_operator(operator='value.zero_amounts')`

**14. run_operator responded**

```
SURVIVED — suite stayed green
..                                                                       [100%]
2 passed in N.NNs
```

**15. tool call** `run_operator(operator='value.null_fields')`

**16. run_operator responded**

```
SURVIVED — suite stayed green
..                                                                       [100%]
2 passed in N.NNs
```

**17. tool call** `run_operator(operator='schema.drop_field')`

**18. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_extraction_has_the_expected_fields - Asser...
LURES ===================================
___________________ test_extraction_has_the_expected_fields ____________________

    def test_extraction_has_the_expected_fields():
        result = extract("invoice_1.txt")
>       assert "vendor" in result
E       AssertionError: assert 'vendor' in {'invoice_number': 'NW-2026-0417', 'date': '2026-03-14', 'total': 1284.5}

tests/test_feature.py:16: AssertionError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_extraction_has_the_expected_fields - Asser...
1 failed, 1 passed in N.NNs
```

**19. tool call** `run_operator(operator='value.transpose_digits')`

**20. run_operator responded**

```
SURVIVED — suite stayed green
..                                                                       [100%]
2 passed in N.NNs
```

**21. tool call** `run_operator(operator='model.echo')`

**22. run_operator responded**

```
killed — FAILED tests/test_feature.py::test_extraction_returns_a_result - ValueError: ...
match = re.search(r"\{.*\}", raw, re.S)
        if not match:
>           raise ValueError(f"model did not return JSON: {raw[:120]!r}")
E           ValueError: model did not return JSON: '                  Subtotal     1,284.50\n                                        VAT (0%)         0.00\n                  '

feature.py:51: ValueError
=========================== short test summary info ============================
FAILED tests/test_feature.py::test_extraction_returns_a_result - ValueError: ...
FAILED tests/test_feature.py::test_extraction_has_the_expected_fields - Value...
2 failed in N.NNs
```


## Phase 3 — remediate: write a test per survivor, and prove it works

**23. tool call** `observe(operator=None)`

**24. observe responded**

```
call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}
```

**25. tool call** `observe(operator='model.downgrade')`

**26. observe responded**

```
call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "02 April 2026", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}
```

**27. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that missed this

```python
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

```

## What was done to the feature

`model.downgrade` — The model behind the feature is swapped for a much weaker one.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

After `model.downgrade`:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "02 April 2026", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

## Your task

Write ONE pytest test that FAILS after `model.downgrade` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**28. `qwen3:8b` answered**

````
```python
from feature import extract

def test_date_format_consistency():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["date"] == "2026-03-14"
    assert result2["date"] == "2026-04-02"
```
````

**29. tool call** `propose_closing_test(operator='model.downgrade')`

the test it is asking the gate to judge:

```python
from feature import extract

def test_date_format_consistency():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["date"] == "2026-03-14"
    assert result2["date"] == "2026-04-02"
```


**30. propose_closing_test responded**

```
accepted: green on the clean feature, red under model.downgrade
________________________

    def test_date_format_consistency():
        result1 = extract("invoice_1.txt")
        result2 = extract("invoice_2.txt")
        assert result1["date"] == "2026-03-14"
>       assert result2["date"] == "2026-04-02"
E       AssertionError: assert '02 April 2026' == '2026-04-02'
E         
E         - 2026-04-02
E         + 02 April 2026

tests/test_greenwash_closing.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_date_format_consistency - Assert...
1 failed in N.NNs
```

**31. tool call** `observe(operator='value.zero_amounts')`

**32. observe responded**

```
call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 0, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 0, "vendor": "AL RAYYAN OFFICE SUPPLIES"}
```

**33. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that missed this

```python
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

```

## What was done to the feature

`value.zero_amounts` — Every monetary amount comes back as zero.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

After `value.zero_amounts`:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 0, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 0, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

## Your task

Write ONE pytest test that FAILS after `value.zero_amounts` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**34. `qwen3:8b` answered**

````
```python
from feature import extract

def test_total_amount_not_zero():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] != 0 and result2["total"] != 0
```
````

**35. tool call** `propose_closing_test(operator='value.zero_amounts')`

the test it is asking the gate to judge:

```python
from feature import extract

def test_total_amount_not_zero():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] != 0 and result2["total"] != 0
```


**36. propose_closing_test responded**

```
accepted: green on the clean feature, red under value.zero_amounts
============================== FAILURES ===================================
__________________________ test_total_amount_not_zero __________________________

    def test_total_amount_not_zero():
        result1 = extract("invoice_1.txt")
        result2 = extract("invoice_2.txt")
>       assert result1["total"] != 0 and result2["total"] != 0
E       assert (0 != 0)

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_total_amount_not_zero - assert (...
1 failed in N.NNs
```

**37. tool call** `observe(operator='value.null_fields')`

**38. observe responded**

```
call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": null, "invoice_number": null, "total": null, "vendor": null}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": null, "invoice_number": null, "total": null, "vendor": null}
```

**39. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that missed this

```python
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

```

## What was done to the feature

`value.null_fields` — Every extracted field is present but null.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

After `value.null_fields`:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": null, "invoice_number": null, "total": null, "vendor": null}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": null, "invoice_number": null, "total": null, "vendor": null}

## Your task

Write ONE pytest test that FAILS after `value.null_fields` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**40. `qwen3:8b` answered**

````
```python
from feature import extract

def test_total_is_not_null():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] is not None
    assert result2["total"] is not None
```
````

**41. tool call** `propose_closing_test(operator='value.null_fields')`

the test it is asking the gate to judge:

```python
from feature import extract

def test_total_is_not_null():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] is not None
    assert result2["total"] is not None
```


**42. propose_closing_test responded**

```
accepted: green on the clean feature, red under value.null_fields
   [100%]
=================================== FAILURES ===================================
____________________________ test_total_is_not_null ____________________________

    def test_total_is_not_null():
        result1 = extract("invoice_1.txt")
        result2 = extract("invoice_2.txt")
>       assert result1["total"] is not None
E       assert None is not None

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_total_is_not_null - assert None ...
1 failed in N.NNs
```

**43. tool call** `observe(operator='value.transpose_digits')`

**44. observe responded**

```
call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1824.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 357.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}
```

**45. asked `qwen3:8b`**

<details><summary>full prompt</summary>

````
You are auditing whether a test suite is worth trusting.

You do not guess. For every sabotage you consider, the harness applies it and
runs the suite, and you are told what happened. A suite that stays green under
sabotage has a blind spot, and the run is the proof.

Your only real job is the last one: given a sabotage the suite missed, and the
values the feature actually returned before and after, write the test that would
have caught it. That test is then run twice — on the clean feature, where it
must pass, and under the sabotage, where it must fail. If it does not do both,
you are shown the pytest output and asked again.

Never report a blind spot that no run demonstrates.

## The feature

```python
"""Invoice field extraction — the feature under test.

Deliberately ordinary: this is the shape of a thousand real LLM features, and
its suite is the shape of a thousand real suites.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Extract these fields from the invoice below and reply with JSON only:
vendor (string), invoice_number (string), date (YYYY-MM-DD string), total (number).

Invoice:
{text}

JSON:"""


# The same instruction, worded differently — what the `prompt.reword` Benign
# Change swaps in. A team edits this line all the time and the feature is not
# broken by it, so the suite is supposed to stay green.
PROMPT_VARIANT = """Read the invoice below and return JSON only, containing:
vendor (string), invoice_number (string), date (string in YYYY-MM-DD form),
total (number).

Invoice:
{text}

JSON:"""


def read_invoice(name: str) -> str:
    return (Path(__file__).parent / "samples" / name).read_text()


def extract(name: str) -> dict:
    """Return the invoice's fields as a dict."""
    text = read_invoice(name)
    raw = complete(PROMPT.format(text=text))
    return _parse(raw)


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"model did not return JSON: {raw[:120]!r}")
    data = json.loads(match.group(0))
    if isinstance(data.get("total"), str):
        cleaned = re.sub(r"[^0-9.]", "", data["total"])
        data["total"] = float(cleaned) if cleaned else 0.0
    return data

```

## The suite that missed this

```python
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

```

## What was done to the feature

`value.transpose_digits` — Digits inside extracted numbers are transposed — 1284.50 becomes 1248.50.

The suite stayed green. Nobody would have noticed.

## What the feature actually returns

Before the sabotage:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1284.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 375.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

After `value.transpose_digits`:

call 1: lambda: feature.extract("invoice_1.txt")
  returned {"date": "2026-03-14", "invoice_number": "NW-2026-0417", "total": 1824.5, "vendor": "NORTHWIND TRADING LLC"}
call 2: lambda: feature.extract("invoice_2.txt")
  returned {"date": "2026-04-02", "invoice_number": "ARO-8821", "total": 357.9, "vendor": "AL RAYYAN OFFICE SUPPLIES"}

## Your task

Write ONE pytest test that FAILS after `value.transpose_digits` and PASSES on the clean
feature. Compare the two observations above and assert on something that
differs.

Rules:
- Reply with Python only. No explanation, no markdown fences.
- Import from `feature`, exactly as the suite above does.
- One function, named `test_...`.
- Call only the calls shown in the observations. Only those model answers are
  recorded; anything else cannot run at all.
- Assert only things that are true of the clean output shown above. A test that
  fails on the clean feature is rejected.

Python:
````

</details>

**46. `qwen3:8b` answered**

````
```python
from feature import extract

def test_total_amount_is_correct():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] == 1284.5 and result2["total"] == 375.9
```
````

**47. tool call** `propose_closing_test(operator='value.transpose_digits')`

the test it is asking the gate to judge:

```python
from feature import extract

def test_total_amount_is_correct():
    result1 = extract("invoice_1.txt")
    result2 = extract("invoice_2.txt")
    assert result1["total"] == 1284.5 and result2["total"] == 375.9
```


**48. propose_closing_test responded**

```
accepted: green on the clean feature, red under value.transpose_digits
========= FAILURES ===================================
_________________________ test_total_amount_is_correct _________________________

    def test_total_amount_is_correct():
        result1 = extract("invoice_1.txt")
        result2 = extract("invoice_2.txt")
>       assert result1["total"] == 1284.5 and result2["total"] == 375.9
E       assert (1824.5 == 1284.5)

tests/test_greenwash_closing.py:6: AssertionError
=========================== short test summary info ============================
FAILED tests/test_greenwash_closing.py::test_total_amount_is_correct - assert...
1 failed in N.NNs
```


## Phase 4 — report

**49. result**

```json
{
  "survivors": [
    "model.downgrade",
    "value.zero_amounts",
    "value.null_fields",
    "value.transpose_digits"
  ],
  "closed": [
    "model.downgrade",
    "value.zero_amounts",
    "value.null_fields",
    "value.transpose_digits"
  ],
  "kill_rate_before": 0.3333
}
```

