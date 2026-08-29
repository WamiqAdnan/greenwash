# Reproduction guide

Written for someone starting from a clean machine with nothing installed but
Python. Everything below runs **offline**: no network, no GPU, no API key, no
Ollama. Every model answer — the corpus features', the baseline's, and the
agent's own — is replayed from recorded fixtures committed in this repository.

## Versions

| | |
|---|---|
| Python | 3.11 (3.10+ works) |
| Dependencies | `pytest>=8.0`, and nothing else |
| Models | `qwen3:8b`, `qwen3:0.6b` and `llama3.1:8b`, via Ollama — **only needed to re-record** |
| Machine the numbers were measured on | Apple M1 Pro, 16 GB |
| Runtime, replayed | about **70 seconds** for everything below |
| Runtime, re-recording from scratch | under an hour, once, with Ollama running |
| Cost to reproduce | $0.00 — no API key, nothing leaves the machine |
| Corpus | 10 cases, 22 hand-confirmed blind spots |

## Setup

```bash
git clone <this repo> && cd greenwash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## The five commands

### 1. How blind are the suites? (~11 s)

```bash
.venv/bin/python evals/run_eval.py -v
```

Applies every applicable Operator to every Corpus Case, runs each case's own
test suite unchanged, and counts. `S` means the sabotage survived — a blind
spot. Ends with `corpus mean kill rate` and a ground-truth check against the
`blindspots.json` a human confirmed by hand.

### 2. The baseline: a model predicting, with no way to check (~1 s)

```bash
.venv/bin/python evals/score_predictions.py baseline/predictions.json
```

Scores the committed one-shot predictions. To regenerate them you need Ollama
(`ollama serve`, `ollama pull qwen3:8b`) and about 15 seconds:

```bash
.venv/bin/python baseline/predict.py --model qwen3:8b
```

### 3. The agent: the same model, allowed to run things (~25 s)

```bash
.venv/bin/python auditor/audit.py
.venv/bin/python evals/score_predictions.py auditor/predictions.json
.venv/bin/python evals/score_predictions.py auditor/prior_predictions.json
```

The first command replays the whole audit — triage, verification, closing tests,
gate rejections and all — and rewrites `auditor/predictions.json`,
`auditor/reports/*.md` and `trajectories/audit-*.jsonl`. Every closing test it
accepts has been run three ways: green on the clean feature, red under the
sabotage it claims to close, and green again under every benign change that moves
that feature's output. The `# gate:` comment above each test in
`auditor/closing_tests/` says which of the three it was actually held to.

The third command is the control: the *same model on the same cases*, scored on
what it expected **before** it ran anything. Prediction versus verification,
one scorer, no other variable.

### 4. The number the user cares about: kill rate before and after (~17 s)

```bash
.venv/bin/python evals/uplift.py
```

Merges the agent's closing tests onto a scratch copy of each case — the suites
themselves are never edited — and re-measures.

### 5. What mutation testing cannot see (~4 s)

```bash
.venv/bin/python evals/brittleness.py
.venv/bin/python evals/leakage.py
```

`brittleness` applies a **benign change** — one that does not break the feature —
and counts closing tests that go red anyway. Read the two lines it prints apart:
the Verification Gate applies some of these changes itself, so that line only
says the gate ran; the **held-out** line is the second opinion and the one to
quote.

`leakage` answers the question mutation testing structurally cannot: is a suite
measuring the feature, or measuring whether the model can repeat its own few-shot
examples? See `corpus/10_few_shot_leak`.

### Greenwash's own tests

```bash
.venv/bin/python -m pytest selftests -q
```

## What you should see

```
$ .venv/bin/python evals/run_eval.py
01_invoice_extractor  [amounts, extraction, llm, structured_output]
  kill rate: 33% (2/6 mutants killed)
  blind spots: model.downgrade, value.zero_amounts, value.null_fields, value.transpose_digits
  ground truth: matches
02_ticket_classifier  [classification, confidence, llm]
  kill rate: 50% (2/4 mutants killed)
  blind spots: classify.collapse, classify.confidence_pin
  ground truth: matches
03_rag_citations  [citations, llm, retrieval]
  kill rate: 0% (0/6 mutants killed)
  blind spots: model.downgrade, model.echo, citation.wrong_page, citation.fabricate, retrieval.truncate, retrieval.shuffle
  ground truth: matches
04_purchase_orders  [amounts, extraction, llm, structured_output]
  kill rate: 100% (5/5 mutants killed)
  - INERT (the sabotage changed nothing the suite could see, not scored): model.downgrade
  ground truth: matches — confirmed clean, no blind spots
05_meeting_summariser  [llm, summarization]
  kill rate: 0% (0/4 mutants killed)
  blind spots: model.downgrade, model.echo, summary.extractive, summary.drop_decisions
  ground truth: matches
06_sql_generator  [llm, sql]
  kill rate: 25% (1/4 mutants killed)
  blind spots: model.downgrade, sql.drop_where, sql.swap_aggregate
  ground truth: matches
07_tool_router  [llm, tool_use]
  kill rate: 50% (2/4 mutants killed)
  blind spots: tool.blank_args, tool.swap_args
  ground truth: matches
08_content_moderation  [llm, moderation]
  kill rate: 50% (1/2 mutants killed)
  - INERT (the sabotage changed nothing the suite could see, not scored): model.downgrade, moderation.miss_implicit
  blind spots: moderation.category_collapse
  ground truth: matches
09_sql_verified  [llm, sql]
  kill rate: 100% (4/4 mutants killed)
  ground truth: matches — confirmed clean, no blind spots
10_few_shot_leak  [classification, llm]
  kill rate: 100% (2/2 mutants killed)
  - INERT (the sabotage changed nothing the suite could see, not scored): model.downgrade
  ground truth: matches — confirmed clean, no blind spots
corpus mean kill rate: 51%  (10 case(s))

$ .venv/bin/python evals/score_predictions.py baseline/predictions.json
baseline-oneshot  model=qwen3:8b  verified=False
OVERALL   precision 55%   recall 73%   f1 0.63
          found 16/22 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/prior_predictions.json
auditor-v1-prior  model=qwen3:8b  verified=False
OVERALL   precision 62%   recall 36%   f1 0.46
          found 8/22 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/predictions.json
auditor-v1  model=qwen3:8b  verified=True
OVERALL   precision 100%   recall 100%   f1 1.00
          found 22/22 confirmed blind spots

$ .venv/bin/python evals/uplift.py
01_invoice_extractor
  kill rate 33% -> 100%   (4 of 4 blind spots closed)
  closed: model.downgrade, value.null_fields, value.transpose_digits, value.zero_amounts
02_ticket_classifier
  kill rate 50% -> 100%   (2 of 2 blind spots closed)
  closed: classify.collapse, classify.confidence_pin
03_rag_citations
  kill rate 0% -> 50%   (3 of 6 blind spots closed)
  closed: citation.fabricate, citation.wrong_page, retrieval.shuffle
  still blind: model.downgrade, model.echo, retrieval.truncate
04_purchase_orders
  no closing tests — nothing to merge
05_meeting_summariser
  kill rate 0% -> 100%   (4 of 4 blind spots closed)
  closed: model.downgrade, model.echo, summary.drop_decisions, summary.extractive
06_sql_generator
  kill rate 25% -> 100%   (3 of 3 blind spots closed)
  closed: model.downgrade, sql.drop_where, sql.swap_aggregate
07_tool_router
  kill rate 50% -> 100%   (2 of 2 blind spots closed)
  closed: tool.blank_args, tool.swap_args
08_content_moderation
  kill rate 50% -> 100%   (1 of 1 blind spots closed)
  closed: moderation.category_collapse
09_sql_verified
  no closing tests — nothing to merge
10_few_shot_leak
  no closing tests — nothing to merge
====================================================
corpus mean kill rate  51% -> 95%   (10 of 10 case(s) reported)
  of which had blind spots to close: 30% -> 93%   (7 case(s))

$ .venv/bin/python evals/brittleness.py
01_invoice_extractor
  schema.add_field: The feature is asked for one more field than it used to return.
    the gate applies this too — a regression check, not a second opinion
    the feature's output moved, and it is still correct
    the case's own suite: green
    closing tests: 0 of 3 raised a FALSE ALARM
  model.swap: the feature returned exactly the same thing — no variation to probe, not measured
  prompt.reword: the feature returned exactly the same thing — no variation to probe, not measured
02_ticket_classifier
  ! model.swap: the case's OWN suite goes red under this. Either the change is not benign or that suite is brittle too — not scored.
  prompt.reword: the feature returned exactly the same thing — no variation to probe, not measured
03_rag_citations
  model.swap: The model behind the feature is swapped for a different one of comparable quality.
    HELD OUT of the gate — nothing upstream enforced this
    the feature's output moved, and it is still correct
    the case's own suite: green
    closing tests: 0 of 2 raised a FALSE ALARM
  prompt.reword: The prompt is reworded to say the same thing differently.
    the gate applies this too — a regression check, not a second opinion
    the feature's output moved, and it is still correct
    the case's own suite: green
    closing tests: 0 of 2 raised a FALSE ALARM
04_purchase_orders
  no closing tests — nothing to probe
05_meeting_summariser
  model.swap: The model behind the feature is swapped for a different one of comparable quality.
    HELD OUT of the gate — nothing upstream enforced this
    the feature's output moved, and it is still correct
    the case's own suite: green
    closing tests: 1 of 1 raised a FALSE ALARM
      - test_summary_contains_key_decisions
  ! prompt.reword: the case's OWN suite goes red under this. Either the change is not benign or that suite is brittle too — not scored.
06_sql_generator
  model.swap: the feature returned exactly the same thing — no variation to probe, not measured
  prompt.reword: the feature returned exactly the same thing — no variation to probe, not measured
07_tool_router
  model.swap: The model behind the feature is swapped for a different one of comparable quality.
    HELD OUT of the gate — nothing upstream enforced this
    the feature's output moved, and it is still correct
    the case's own suite: green
    closing tests: 1 of 2 raised a FALSE ALARM
      - test_issue_refund_arguments_are_correct
  prompt.reword: the feature returned exactly the same thing — no variation to probe, not measured
08_content_moderation
  model.swap: the feature returned exactly the same thing — no variation to probe, not measured
  prompt.reword: the feature returned exactly the same thing — no variation to probe, not measured
09_sql_verified
  no closing tests — nothing to probe
10_few_shot_leak
  no closing tests — nothing to probe
====================================================
false alarm rate  2/5 (40%)  under HELD-OUT benign changes — the gate never saw these, so this is the number that counts
                  0/5 (0%)  under benign changes the gate applies itself — a regression check on the gate

$ .venv/bin/python evals/leakage.py
10_few_shot_leak
  as shipped
    in the prompt : 5/5   — these are the suite's test cases, so this is what it scores
    held out      : 5/5   — the suite has never seen these
  under model.downgrade
    in the prompt : 5/5   — these are the suite's test cases, so this is what it scores
    held out      : 4/5   — the suite has never seen these
      h4: expected 'account', got 'billing'
====================================================
10_few_shot_leak: the suite scores 5/5 as shipped and 5/5 with the model swapped for one 13x smaller, so it cannot tell them apart. On tickets it has never seen, the small model gets 4/5.
Kill Rate cannot find this. Every sabotage breaks the in-prompt examples too, so the suite goes red and looks healthy.
```

Three predictors, one scorer, one ground truth: the baseline predicting (0.63),
the *same model* predicting inside the agent before it ran anything (0.46), and
the agent after verification (1.00) — 22 of 22 confirmed blind spots, and nothing
invented on either control. The gap between the first two and the third is the
harness, not the model. The prior's score is unstable across re-recordings — it
has been 0.24, 0.35, 0.42, 0.46 and 0.47 on identical cases, moved by nothing but
rewordings of the prompt that asks for it, which is itself part of the argument.

`04_purchase_orders` and `09_sql_verified` are the **precision controls** — suites
that catch everything, on deliberately different capabilities. The agent reports
nothing on either. The baseline reports sabotages missed on both, and those false
alarms are most of why its precision is 55%.

`evals/uplift.py` closes more blind spots than the agent claimed to close. That
is not a bookkeeping error: a closing test written for one sabotage often kills
others. On case 03 the test written for `citation.fabricate` checks every
citation's quote against the document, so it also catches `citation.wrong_page`.

`evals/brittleness.py` prints two populations and they mean different things.
`0 of 5` is under the benign changes the Gate applies before accepting a test —
its own rule, read back. `2 of 5` is under the **held-out** `model.swap`, which
the Gate never sees, and that 40% is the honest figure for over-fitting. Both
false alarms are shipped tests: one asserts the literal string
`"starter tier price"` where a different model writes "the price of the starter
tier at $29".

The Gate does work where it can see. During the recorded run it rejected a
candidate on case 03 that had hard-coded both of the model's answers verbatim —
the rejection and the pytest output that caused it are in
`trajectories/audit-03_rag_citations.md`, and that survivor ships with no closing
test, which is why the report lists it as still open.

Case 02 is the one case no benign change can reach, and the gap is worth seeing
for yourself:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from auditor.agent import CLOSING_TEST_FILE, DEFAULT_SCRATCH
from greenwash import harness; from pathlib import Path
case = harness.Case(Path('corpus/02_ticket_classifier'))
code = Path('auditor/closing_tests/02_ticket_classifier.py').read_text()
m = harness.overlay(case, {CLOSING_TEST_FILE: code}, DEFAULT_SCRATCH/'manual')
print(m.run_suite('model.swap', select=f'tests/{CLOSING_TEST_FILE}')[1][-400:])"
```

`test_confidence_pin_bypassed` goes red on `assert 0.9 == 0.95` — a shipped test
pinning the model's exact confidence values, on the one case the gate cannot
check. `schema.add_field` is for extraction features, `prompt.reword` is inert
there, and `model.swap` takes the suite's own LLM judge down with it, so the
probe refuses to score it: a brittle test cannot be told from a brittle suite
when both are red. The two closing tests in
`auditor/closing_tests/02_ticket_classifier.py` say so themselves — their
`# gate:` line reads `no benign change is measurable on this feature`.

## Reproducing the recordings (needs Ollama)

Only necessary if you want to regenerate the fixtures rather than replay them.

```bash
ollama serve &
ollama pull qwen3:8b && ollama pull qwen3:0.6b && ollama pull llama3.1:8b

# corpus fixtures — two passes per case, one per model, for all ten cases
for c in corpus/*/; do
  .venv/bin/python scripts/record_fixtures.py --case $(basename $c) --model qwen3:8b
  .venv/bin/python scripts/record_fixtures.py --case $(basename $c) --model qwen3:0.6b
done

# the baseline and the agent, live
.venv/bin/python baseline/predict.py
.venv/bin/python auditor/audit.py --record
.venv/bin/python scripts/render_trajectory.py --all
```

Two passes, three models. `qwen3:0.6b` is not optional — the `model.downgrade`
Operator swaps the feature onto it, and that mutant cannot run without its own
recordings. `llama3.1:8b` needs no pass of its own: the held-out `model.swap`
Benign Change is applied inside the `qwen3:8b` pass and sets the model itself.
You do have to have pulled it.

The whole regeneration is under an hour on an M1 Pro and costs nothing but
electricity. Recording never deletes, so sweep `auditor/fixtures/` afterwards —
the reachable keys are the `"kind": "prompt"` events in `trajectories/`.

## A reproducibility check you can run

Trajectories carry no timestamps, and captured pytest output is normalised, so a
replayed audit rewrites them byte for byte:

```bash
.venv/bin/python auditor/audit.py && git diff --stat trajectories/
```

An empty diff means your replay matched the recorded run exactly.
