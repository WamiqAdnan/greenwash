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
| Models | `qwen3:8b` and `qwen3:0.6b`, via Ollama — **only needed to re-record** |
| Machine the numbers were measured on | Apple M1 Pro, 16 GB |
| Cost to reproduce | $0.00 |

## Setup

```bash
git clone <this repo> && cd greenwash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## The four commands

### 1. How blind are the suites? (~3 s)

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

### 3. The agent: the same model, allowed to run things (~10 s)

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

### 4. The number the user cares about: kill rate before and after (~6 s)

```bash
.venv/bin/python evals/uplift.py
```

Merges the agent's closing tests onto a scratch copy of each case — the suites
themselves are never edited — and re-measures.

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
corpus mean kill rate: 46%  (4 case(s))

$ .venv/bin/python evals/score_predictions.py baseline/predictions.json
baseline-oneshot  model=qwen3:8b  verified=False
OVERALL   precision 41%   recall 58%   f1 0.48
          found 7/12 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/prior_predictions.json
auditor-v1-prior  model=qwen3:8b  verified=False
OVERALL   precision 60%   recall 25%   f1 0.35
          found 3/12 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/predictions.json
auditor-v1  model=qwen3:8b  verified=True
OVERALL   precision 100%   recall 100%   f1 1.00
          found 12/12 confirmed blind spots

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
====================================================
corpus mean kill rate  46% -> 88%   (4 of 4 case(s) reported)
  of which had blind spots to close: 28% -> 83%   (3 case(s))

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
====================================================
false alarm rate  0/2 (0%)  under HELD-OUT benign changes — the gate never saw these, so this is the number that counts
                  0/5 (0%)  under benign changes the gate applies itself — a regression check on the gate
```

Three predictors, one scorer, one ground truth: the baseline predicting (0.48),
the *same model* predicting inside the agent before it ran anything (0.35), and
the agent after verification (1.00). The gap between the first two and the third
is the harness, not the model. The prior's score is unstable across re-recordings
— it has been 0.24, 0.35, 0.42 and 0.47 on identical cases, moved by nothing but
rewordings of the prompt that asks for it — which is itself part of the argument:
prediction with this model lands somewhere between 0.24 and 0.61 depending on how
you ask, and verification lands on 1.00 every time.

`04_purchase_orders` is the control — a suite that catches everything. The agent
reports nothing there. The baseline reports all six sabotages as missed, which is
six false alarms, and that is most of why its precision is 41%.

`evals/uplift.py` closes more blind spots than the agent claimed to close. That
is not a bookkeeping error: a closing test written for one sabotage often kills
others. On case 03 the test written for `citation.fabricate` checks every
citation's quote against the document, so it also catches `citation.wrong_page`.

`evals/brittleness.py` is the number that keeps uplift honest, and it can only
reach case 03 — rewording a prompt does not change what an extraction feature
returns, so those cases are reported *not measured* rather than passing.

Read the two lines apart. The Verification Gate applies `prompt.reword` itself
before accepting a closing test, so that line is the gate's own rule reported
back. `model.swap` is **held out** — the gate is not allowed to apply it — so
that line is a second opinion, and it is the one to quote. The gate rejected
exactly one candidate on this rule during the recorded run: case 03,
`model.echo`, attempt 1, which had hard-coded both of the model's answers
verbatim. The rejection and the pytest output that caused it are in
`trajectories/audit-03_rag_citations.md`; that survivor ends with no closing test,
which is why the report lists it as still open.

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
ollama pull qwen3:8b && ollama pull qwen3:0.6b

# corpus fixtures, both models, per case
.venv/bin/python scripts/record_fixtures.py --case 01_invoice_extractor --model qwen3:8b
.venv/bin/python scripts/record_fixtures.py --case 01_invoice_extractor --model qwen3:0.6b

# the agent, live — about 7 minutes on an M1 Pro
.venv/bin/python auditor/audit.py --record
.venv/bin/python scripts/render_trajectory.py --all
```

`qwen3:0.6b` is not optional: the `model.downgrade` Operator swaps the feature
onto it, and that mutant cannot run without its own recordings.

## A reproducibility check you can run

Trajectories carry no timestamps, and captured pytest output is normalised, so a
replayed audit rewrites them byte for byte:

```bash
.venv/bin/python auditor/audit.py && git diff --stat trajectories/
```

An empty diff means your replay matched the recorded run exactly.
