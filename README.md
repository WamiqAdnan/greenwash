# Greenwash

**Your eval suite is green. That is a claim, not evidence.**

Greenwash breaks the code your suite guards — deliberately, one sabotage at a
time — and reports every break your tests slept through, with the failing run
attached.

> Built for the micro1 Agentic Workflows Hackathon, 28–31 August 2026.
> Status: the auditor agent works end to end. See `STATE.md`.

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

## The agent

Finding the holes is the easy half. The agent — `auditor/audit.py` — also writes
the tests that close them, and it is not trusted to do either.

It **never predicts** which sabotages survive. It applies each one, runs your
suite, and reads the result. Then, for each survivor, it is shown what the
feature actually returned before and after the sabotage and asked for the
assertion that would have caught it. Every test it writes is then run twice —
green on the clean feature, red under the sabotage — or it goes back with the
pytest output attached. **A test that does not do both is never reported.**

The whole agent runs on `qwen3:8b` on a laptop, because the hard part is the
harness's job, not the model's.

| | precision | recall | F1 | blind spots found |
|---|---|---|---|---|
| the same model, predicting (baseline) | 64% | 58% | 0.61 | 7 / 12 |
| the same model, predicting (inside the agent, before it ran anything) | 80% | 33% | 0.47 | 4 / 12 |
| **the agent, after running them** | **100%** | **100%** | **1.00** | **12 / 12** |

One scorer, one ground truth, three predictors. Reaching 12/12 is not cleverness
and is not claimed as any — it is what happens when you stop guessing and run
the thing. The number that took work is the next one.

**Kill rate across the corpus: 28% → 75%**, measured by `evals/uplift.py` from
the tests the agent wrote, outside the agent, on a scratch copy — your suite is
evidence and is never edited.

### What it got wrong, which is the more interesting half

Asked to catch a sabotage that routes every ticket to `billing`, it wrote
`assert result["label"] == "billing"` — a test asserting the bug is present.
Three times. The gate rejected all three and that hole is still reported open.
An agent that writes tests from observed output will happily codify the bug it
was shown; the gate is what makes a small model's assertions safe to ship.

And some tests it *did* get through the gate pin the model's exact prose, which
kills every mutant and would fire on a legitimate model upgrade. Mutation
testing rewards over-fitting. That is the project's main failure mode and it is
written up in `CHANGELOG.md` with the measurement that is missing.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python evals/run_eval.py -v      # how blind are the suites?
.venv/bin/python auditor/audit.py          # the agent, replayed
.venv/bin/python evals/uplift.py           # kill rate before -> after
```

No network, no GPU, no API key — every model answer replays from `fixtures/`,
the agent's own answers included. The whole pipeline is under 20 seconds and was
verified with Ollama stopped. Step-by-step from a clean machine, with the output
you should see: `REPRODUCE.md`.

## Reading order

`CONTEXT.md` for the vocabulary · `REPRODUCE.md` to run it · `STATE.md` for
where the work is · `CHANGELOG.md` for how it got here, including the main
failure mode · `auditor/reports/` for what the user actually reads ·
`trajectories/` for what both agents did, step by step.
