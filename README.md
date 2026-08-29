# Greenwash

**Your eval suite is green. That is a claim, not evidence.**

Greenwash breaks the code your suite guards — deliberately, one sabotage at a
time — and reports every break your tests slept through, with the failing run
attached.

> Built for the micro1 Agentic Workflows Hackathon, 28–31 August 2026.
> Ten corpus cases, 22 hand-confirmed blind spots, everything replayable
> offline in about 70 seconds. See `STATE.md`.

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

The sharpest one is `corpus/07_tool_router`. Its suite asserts that the right
tool fires — because firing the *wrong* tool is what went wrong in early testing,
so that is what everyone wrote tests for. Greenwash swaps two argument values:

```
issue_refund(order_id="A-4471", amount=84.0)     ->  what it should call
issue_refund(order_id=84.0, amount="A-4471")     ->  what it calls now
```

The right tool fires. The suite is green. **The assertion everybody writes is
the one that catches the failure nobody has.**

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
| the same model, predicting (baseline) | 55% | 73% | 0.63 | 16 / 22 |
| the same model, predicting (inside the agent, before it ran anything) | 62% | 36% | 0.46 | 8 / 22 |
| **the agent, after running them** | **100%** | **100%** | **1.00** | **22 / 22** |

One scorer, one ground truth, three predictors. Reaching 22/22 is not cleverness
and is not claimed as any — it is what happens when you stop guessing and run
the thing. The number that took work is the next one.

The middle row is worth a second look: it is the *same model on the same cases*,
and the only thing taken away from it is the ability to run anything. Across
re-records it has scored 0.24, 0.35, 0.42, 0.46 and 0.47, moved by nothing but
rewordings of the prompt that asks it the question. Prediction with this model
lands somewhere in that band. Verification lands on 1.00 every time.

**Kill rate across the corpus: 51% → 75%**, measured by `evals/uplift.py` from
the tests the agent wrote, outside the agent, on a scratch copy — your suite is
evidence and is never edited. Over the seven cases that had blind spots to close
at all: 30% → 64%.

That number used to read 95%. It came down because four of the thirteen tests it
counted were brittle — they would have fired the next time somebody changed a
model — and the gate now rejects tests like that instead of shipping them.
**Twenty points of the old number was over-fitting.** See `CHANGELOG.md`.

### The comparison, in one table

| metric | simple baseline | agent solution | change |
|---|---|---|---|
| blind spots found (F1 against hand-confirmed truth) | 0.63 | **1.00** | +0.37 |
| — of 22 real ones | 16, plus 13 false alarms | **22, and no false alarms** | |
| kill rate after the run | 51% — it writes no tests | **75%** | +24 pts |
| false alarms in the tests it ships | n/a — ships none | **0 of 3 held out, 0 of 8 checked** | measured, not assumed |
| human time per case | — | 7 s replayed, one pass to record | see below |
| API cost per case | $0 | $0 | runs on a laptop |

Both rows are `qwen3:8b`, on the same ten cases, scored by the same scorer. The
only variable is whether the model is allowed to run anything.

*Human time* is the row without a measured baseline, so it is marked as an
estimate and not claimed as a result: auditing one suite by hand — reading every
assertion, imagining every silent failure, writing the adversarial cases — is
half a day of senior time in our experience, against 7 seconds of replay. What
*is* measured is that the whole pipeline runs offline in about 70 seconds, and
that recording every fixture from scratch against Ollama takes under an hour on
an M1 Pro, once.

### The controls

Two cases in the corpus have **good** suites, and they are there to catch the
tool crying wolf. `04_purchase_orders` checks the arithmetic, the formats, the
document's own facts and that what came back is really in the source.
`09_sql_verified` runs each generated query against a fixture database and checks
the answer against numbers worked out by hand. They are deliberately on different
capabilities, because a control only proves precision for the kind of feature it
covers.

Greenwash reports **nothing** on either, because it ran the sabotages and watched
them die. The baseline calls sabotages missed on both. A predictor with no way to
check cannot tell a good suite from a bad one — which is most of why its
precision is 55%.

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
wearing two hats, so one benign change is always **held out** of the gate and
reserved for `brittleness.py`. That split is what makes the probe's number mean
anything, and the first time it had a real corpus to work on it found **two of
five** shipped tests brittle — a snapshot of the model's prose, and a pinned
argument dict.

So the gate got the change that catches them, and a third one besides. Both are
gone now, along with two more the next held-out change turned up:

```
0 of 8   under the benign changes the gate checks
0 of 3   under the benign change it never sees
```

That took twenty points off the headline, because four of the thirteen tests the
agent used to ship were the brittle ones. **A tool that reports a lower number
after being made more honest is working.**

Two things that cost is buying, and one it is not. The gate now rejects nine
candidates as false alarms across the corpus. The tests that survive are checked
against two different model swaps and a reworded prompt. And the `0 of 3` is a
narrower audit than the `2 of 5` it replaced — three tests on one capability —
so it is not proof that nothing is brittle, just the strongest thing the
remaining slot can say.

## What it cannot do

`10_few_shot_leak` is a suite whose five test cases are the model's own five
few-shot examples. Exact-label assertions, every label covered, the house
convention asserted explicitly — nothing about it looks weak.

Greenwash gives it a **100% kill rate and zero blind spots.** That answer is
correct. Every sabotage breaks the in-prompt examples too, so the suite goes red,
so the suite looks healthy. The suite is still worthless: it measures whether the
model can repeat what it was just shown. It cannot even tell the shipped model
from one 13× smaller, because the answers are in the prompt — Greenwash reports
that swap as *inert*, which is literally true.

What sees it is holding examples back. `evals/leakage.py` runs the same feature
over tickets the suite has never seen:

```
as shipped              5/5 in the prompt    5/5 held out
under model.downgrade   5/5 in the prompt    4/5 held out   <- the suite scores these identically
```

**Mutation testing scores the assertions you wrote against the cases you chose.
It cannot audit the cases.** Case 08 shows the same hole from the other side: a
moderation suite whose examples are all obvious is blind to implicit abuse in a
way no operator can demonstrate, and Greenwash correctly reports *inert* and
correctly reports nothing. If you build one of these, build the held-out check
too. `CHANGELOG.md` has the receipts and the full hot take.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python evals/run_eval.py -v      # how blind are the suites?   11 s
.venv/bin/python auditor/audit.py          # the agent, replayed         25 s
.venv/bin/python evals/uplift.py           # kill rate before -> after   17 s
.venv/bin/python evals/brittleness.py      # do the new tests cry wolf?   4 s
.venv/bin/python evals/leakage.py          # is a suite testing its own prompt?
```

No network, no GPU, no API key — every model answer replays from `fixtures/`,
the agent's own answers included. The whole pipeline is about **70 seconds** and
was verified with Ollama stopped. Step-by-step from a clean machine, with the
output you should see: `REPRODUCE.md`.

## Reading order

`CONTEXT.md` for the vocabulary · `REPRODUCE.md` to run it · `STATE.md` for
where the work is · `CHANGELOG.md` for how it got here, including the main
failure mode · `auditor/reports/` for what the user actually reads ·
`trajectories/` for what both agents did, step by step.
