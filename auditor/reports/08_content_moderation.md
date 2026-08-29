# Trust Report — 08_content_moderation

**The feature.** Flags posts that violate content policy and assigns a category.

**The suite.** Three obvious cases — clear abuse, clear spam, clearly fine. No implicit or coded content, which is the content moderation actually exists for.

**Kill rate: 50%** — 1 of 2 sabotages were noticed.

1 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

1 of them now has a test that would have caught it.

## `moderation.category_collapse`

Everything flagged comes back under the same category.

- suite under this sabotage: **suite stayed green**
- closing test: verified green on the clean feature, red under moderation.category_collapse, no benign change is measurable on this feature
- it fails as: `FAILED tests/test_greenwash_closing.py::test_category_for_p1_is_harassment_before_sabotage`
- attempts needed: 1

```python
from feature import moderate

def test_category_for_p1_is_harassment_before_sabotage():
    result = moderate("p1")
    assert result["category"] == "harassment"
    assert result["flagged"] is True
```

## Tried, and nothing happened

These sabotages were applied and your feature returned exactly what it returned before. Your suite stayed green because there was nothing to notice — this is not a hole:

- `moderation.miss_implicit`
- `model.downgrade`

## What the auditor expected, before it ran anything

Predicted misses: `moderation.miss_implicit`

Actually missed: `moderation.category_collapse`

> The suite lacks tests for implicit content, which the sabotage would allow through undetected.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
