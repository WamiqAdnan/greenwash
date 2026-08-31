# Trust Report — 04_purchase_orders

**The feature.** Extracts header fields and line items from a purchase order with a local LLM.

**The suite.** The control: a suite that actually checks. Types, formats, the arithmetic, the values against the document, and that the vendor it returned is really in the source.

**Kill rate: 100%** — 5 of 5 sabotages were noticed.

No sabotage survived this suite.

## Tried, and nothing happened

These sabotages were applied and your feature returned exactly what it returned before. Your suite stayed green because there was nothing to notice — this is not a hole:

- `model.downgrade`

## What the auditor expected, before it ran anything

Predicted misses: `schema.drop_field`, `model.downgrade`

Actually missed: (none)

> The suite checks for presence of fields and their types, but does not verify that all required fields are present. It also does not check for the presence of fields that might be silently dropped or that the model might be downgraded to a weaker version.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
