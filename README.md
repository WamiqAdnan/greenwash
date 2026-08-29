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
assertion that would have caught it. Every test it writes is then run three ways
— green on the clean feature, red under the sabotage, and green again under a
change that breaks nothing — or it goes back with the pytest output attached.
**A test that does not do all three is never reported.**

The whole agent runs on `qwen3:8b` on a laptop, because the hard part is the
harness's job, not the model's.

| | precision | recall | F1 | blind spots found |
|---|---|---|---|---|
| the same model, predicting (baseline) | 41% | 58% | 0.48 | 7 / 12 |
| the same model, predicting (inside the agent, before it ran anything) | 40% | 17% | 0.24 | 2 / 12 |
| **the agent, after running them** | **100%** | **100%** | **1.00** | **12 / 12** |

One scorer, one ground truth, three predictors. Reaching 12/12 is not cleverness
and is not claimed as any — it is what happens when you stop guessing and run
the thing. The number that took work is the next one.

The middle row is worth a second look: it is the *same model on the same cases*,
and the only thing taken away from it is the ability to run anything. It has also
scored 0.42 on this corpus — rewording the prompt that asks the question moved it
that far. Prediction with this model lands somewhere between 0.24 and 0.61
depending on how you ask it. Verification lands on 1.00 every time.

**Kill rate across the corpus: 46% → 88%**, measured by `evals/uplift.py` from
the tests the agent wrote, outside the agent, on a scratch copy — your suite is
evidence and is never edited. Over the three cases that had blind spots to close
at all: 28% → 83%.

### The control

One case in the corpus has a **good** suite — it checks the arithmetic, the
formats, the document's own facts, and that what came back is really in the
source. It is there to catch the tool crying wolf, and it is the reason the
baseline's precision is 41% rather than 64%: asked about the strong suite, the
baseline called **all six** sabotages missed, when the suite catches every one.
A predictor with no way to check cannot tell a good suite from a bad one. The
agent reports nothing there, because it ran them and watched them die.

That case also turned up something the tool had been getting wrong. Swapping in
the 13× smaller model left this feature's output **byte-identical**, so the suite
stayed green with nothing to catch. That is not a blind spot, and Greenwash now
says so — a mutant whose sabotage changes nothing observable is reported *inert*
and kept out of the kill rate entirely.

### What it got wrong, which is the more interesting half

Asked to catch a sabotage that routes every ticket to `billing`, it wrote
`assert result["label"] == "billing"` — a test asserting the bug is present.
Three times. The gate rejected all three and that hole is still reported open.
An agent that writes tests from observed output will happily codify the bug it
was shown; the gate is what makes a small model's assertions safe to ship.

The second failure is subtler and it is the one mutation testing *rewards*. Some
tests the agent wrote pinned the model's exact prose. A test like that kills
every mutant and passes the gate honestly — and goes red the next time somebody
rewords a prompt. By kill rate it is a perfect test; to you it is a pager at 3am
for nothing.

Kill rate structurally cannot see that, so there is a second measurement that
can. `evals/brittleness.py` applies a **benign change** — something a team really
does, like rewording the prompt, which does not break anything — and counts the
new tests that go red anyway. Those are false alarms.

```
run_eval      apply a sabotage.       The suite SHOULD go red.    Green = blind spot.
brittleness   apply a benign change.  The suite SHOULD stay green. Red = false alarm.
```

It caught the first version of the agent doing exactly this: 1 of 1 measurable
test fired on output that was correct.

So the benign changes moved **inside the gate**. A test is now run three ways —
green on your feature, red under the sabotage it claims to catch, and green again
under a change that breaks nothing — and it is dropped if it fails any of them.
On its first run the gate caught a test that had hard-coded both of the model's
answers verbatim. It would have shipped under the old two runs. It did not ship.

A gate that enforces a rule and a probe that checks the same rule are one thing
wearing two hats, so one benign change is **held out** of the gate: `model.swap`
moves the feature onto a different vendor's model, and only `brittleness.py` is
allowed to apply it. Its `0 of 2` is therefore evidence about the tests rather
than a report that the gate ran. The probe prints the two populations apart, and
you should read the held-out line.

What is *not* fixed is coverage, and here is the receipt. Neither benign change
moves what an extraction feature returns — the same JSON comes back however you
word the prompt and whichever model reads the invoice — so the gate still only
bites on **one case in four**. Run case 02's closing tests under `model.swap` by
hand and one of them goes red on `assert 0.9 == 0.95`: a shipped test pinning the
model's exact confidence values, on a case the gate never checked. The probe
declines to count it, correctly, because that case's own suite goes red too and
a brittle test and a brittle suite look identical from outside. So: the failure
mode is structural where it can be seen, and there is a known blind spot in where
it can be seen. `CHANGELOG.md` has the receipts.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python evals/run_eval.py -v      # how blind are the suites?
.venv/bin/python auditor/audit.py          # the agent, replayed
.venv/bin/python evals/uplift.py           # kill rate before -> after
.venv/bin/python evals/brittleness.py     # do the new tests cry wolf?
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
