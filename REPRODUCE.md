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
`auditor/reports/*.md` and `trajectories/audit-*.jsonl`.

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
corpus mean kill rate: 28%  (3 case(s))

$ .venv/bin/python evals/score_predictions.py baseline/predictions.json
baseline-oneshot  model=qwen3:8b  verified=False

====================================================
OVERALL   precision 64%   recall 58%   f1 0.61
          found 7/12 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/prior_predictions.json
auditor-v1-prior  model=qwen3:8b  verified=False

====================================================
OVERALL   precision 80%   recall 33%   f1 0.47
          found 4/12 confirmed blind spots

$ .venv/bin/python evals/score_predictions.py auditor/predictions.json
auditor-v1  model=qwen3:8b  verified=True

====================================================
OVERALL   precision 100%   recall 100%   f1 1.00
          found 12/12 confirmed blind spots

$ .venv/bin/python evals/uplift.py
01_invoice_extractor
  kill rate 33% -> 100%   (4 of 4 blind spots closed)
  closed: model.downgrade, value.null_fields, value.transpose_digits, value.zero_amounts
02_ticket_classifier
  kill rate 50% -> 75%   (1 of 2 blind spots closed)
  closed: classify.confidence_pin
  still blind: classify.collapse
03_rag_citations
  kill rate 0% -> 50%   (3 of 6 blind spots closed)
  closed: model.downgrade, model.echo, retrieval.truncate
  still blind: citation.fabricate, citation.wrong_page, retrieval.shuffle
====================================================
corpus mean kill rate  28% -> 75%   (3 of 3 case(s) reported)
```

Three predictors, one scorer, one ground truth: the baseline predicting (0.61),
the *same model* predicting inside the agent before it ran anything (0.47), and
the agent after verification (1.00). The gap between the first two and the third
is the harness, not the model.

`evals/uplift.py` closes more blind spots than the agent claimed to close (8
against 6). That is not a bookkeeping error: a closing test written for one
sabotage often kills others, and one of them is a snapshot assertion that fails
on any change to the output at all. See the Improvement Changelog — this is the
project's own main failure mode.

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
