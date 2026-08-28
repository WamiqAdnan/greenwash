# Greenwash

**Your eval suite is green. That is a claim, not evidence.**

Greenwash breaks the code your suite guards — deliberately, one sabotage at a
time — and reports every break your tests slept through, with the failing run
attached.

> Built for the micro1 Agentic Workflows Hackathon, 28–31 August 2026.
> Status: measurement rig complete, auditor agent not yet built. See `STATE.md`.

## The user

An engineer who owns a shipped LLM feature and has been asked to approve a model
swap. Their suite is green. It says 94%.

They have no way to know whether 94% means the feature works or means the
assertions cannot fail. Finding out by hand means auditing every assertion,
imagining every failure mode, and writing the adversarial cases — days of senior
time spent auditing your own blind spots, which is the one thing you are
structurally bad at.

## Why it matters

Here is a suite from `corpus/01_invoice_extractor`. Nothing about it is a
strawman; these are assertions people write:

```python
def test_extraction_has_the_expected_fields():
    result = extract("invoice_1.txt")
    assert "vendor" in result
    assert "invoice_number" in result
    assert "total" in result
```

Greenwash swaps the model underneath it for one thirteen times smaller. The
smaller model returns `"02 April 2026"` where the schema demands `YYYY-MM-DD`.

**The suite passes.**

It also passes when every amount is replaced with zero, when every field is
nulled, and when digits inside the totals are transposed. Measured Kill Rate:
**33%**. Two thirds of the ways that feature can break, it breaks silently.

`corpus/03_rag_citations` scores **0%**. Its suite checks that citations exist
and never that they are true, so it survives fabricated quotes, wrong pages,
truncated retrieval, and a model replaced by one that echoes its input back.

## How it works

Mutation testing, with operators that mean something for AI features. Classic
mutation testing flips `>` into `>=`; that finds nothing here. These are the
ways an LLM feature breaks quietly:

| | |
|---|---|
| `model.downgrade` | the model is swapped for a much weaker one |
| `citation.fabricate` | citations become plausible quotes found nowhere in the source |
| `retrieval.truncate` | only half the retrieved context reaches the model |
| `classify.collapse` | every input gets the most common label |
| `value.zero_amounts` | every monetary amount comes back zero |

For each one: sabotage the feature, run the team's own suite unchanged. Red means
the suite noticed. Green means you have found a blind spot, and the run is the
receipt.

The tool cannot invent a finding. A blind spot exists only when a real sabotage
survived a real test run.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python evals/run_eval.py -v
```

No network, no GPU, no API key — every model answer replays from `fixtures/`.
Under 3 seconds for the current three cases — verified from a clean clone. Full setup, recording, and expected
output: see `AGENTS.md`.

## Reading order

`CONTEXT.md` for the vocabulary · `STATE.md` for where the work is ·
`CHANGELOG.md` for how it got here, including what was removed.
