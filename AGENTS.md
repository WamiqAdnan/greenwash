# Working on Greenwash

Read `CONTEXT.md` first — it defines every capitalised term used here and in the
code. Read `STATE.md` second — it says where the work actually is.

## What this is

Greenwash breaks the code an eval suite guards and checks whether the suite
notices. Hackathon submission, deadline **Mon 31 Aug 2026, 18:00 UTC**
(22:00 Asia/Dubai). Requirements are in `micro1-instructions.pdf`.

## Run it

```bash
.venv/bin/python evals/run_eval.py -v            # whole corpus
.venv/bin/python evals/run_eval.py --case 01_invoice_extractor -v
```

Needs no network and no GPU: every model answer is replayed from `fixtures/`.
A full sweep of the current three cases takes about a minute.

Recording new fixtures *does* need Ollama running (`ollama serve`):

```bash
.venv/bin/python scripts/record_fixtures.py --case 03_rag_citations --model qwen3:8b
.venv/bin/python scripts/record_fixtures.py --case 03_rag_citations --model qwen3:0.6b
```

Both models are required for every case — `model.downgrade` swaps the feature
onto `qwen3:0.6b` and dies without its fixtures.

## The rules that matter

**Never edit a Corpus Case's suite to make a point.** The suites are the
evidence. If a suite is too strong or too weak, change the *feature* or add a
new case; a suite edited to produce a nicer number is a fabricated result.

**A red suite is not automatically a Kill.** If Greenwash itself broke, the
Mutant is Invalid and must not be scored. `HARNESS_FAULTS` in
`greenwash/harness.py` lists the signatures. When you add an Operator that can
fail in a new way, add its signature there. This bug was real and it inflated
the headline number by 17 points — see `CHANGELOG.md`.

**Ground truth is confirmed by hand, not by the harness.** `blindspots.json`
records Survivors a human has actually looked at. When measured and confirmed
diverge, the eval says MISMATCH and you investigate — you do not update the
JSON to match.

**Every claim in the submission needs a run behind it.** Ground rule 09.

## Adding a Corpus Case

1. `corpus/NN_name/` with `case.json` (`description`, `tags`, `suite_looks_like`)
2. `feature.py` — expose work through module-level names an Operator can replace
3. `conftest.py` — copy an existing one verbatim; it applies `GREENWASH_MUTATION`
   before pytest imports the tests
4. `tests/test_feature.py` — a suite a real team would plausibly have written.
   No strawmen. Every assertion must be one people actually write.
5. `record_plan.py` — every model call the suite makes
6. Record fixtures for **both** models
7. Run the eval, look at each Survivor by hand, then write `blindspots.json`

## Layout

```
greenwash/         operators.py (the sabotage library), harness.py (the loop),
                   modelclient.py (record/replay seam)
corpus/NN_*/       one Corpus Case each
evals/run_eval.py  the measurement the Changelog reports against
scripts/           record_fixtures.py
trajectories/      agent traces — required deliverable, capture from run one
docs/adr/          decisions worth their own file
```

## Conventions

Comments explain *why*, at the altitude of the domain — see `greenwash/harness.py`.
Do not narrate what the code plainly does. Match `CONTEXT.md` vocabulary exactly;
if you need a word that is not in it, add it there first.
