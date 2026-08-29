# Working on Greenwash

Read `CONTEXT.md` first — it defines every capitalised term used here and in the
code. Read `STATE.md` second — it says where the work actually is.

## What this is

Greenwash breaks the code an eval suite guards and checks whether the suite
notices. Hackathon submission, deadline **Mon 31 Aug 2026, 18:00 UTC**
(22:00 Asia/Dubai). Requirements are in `micro1-instructions.pdf`.

## Run it

```bash
.venv/bin/python evals/run_eval.py -v            # kill rate per case, ~3s
.venv/bin/python auditor/audit.py                # the agent, replayed, ~20s
.venv/bin/python evals/score_predictions.py auditor/predictions.json
.venv/bin/python evals/uplift.py                 # kill rate before -> after
.venv/bin/python evals/brittleness.py            # do the new tests cry wolf?
.venv/bin/python -m pytest selftests -q          # greenwash's own tests
```

Needs no network and no GPU: every model answer is replayed from `fixtures/`,
the Auditor's own answers included. A full sweep of the current three cases
takes about 3 seconds.

Re-running the Auditor against Ollama, which rewrites `auditor/fixtures/` and
the Trajectories:

```bash
ollama serve &
.venv/bin/python auditor/audit.py --record       # ~7 min on an M1 Pro
.venv/bin/python scripts/render_trajectory.py --all
```

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

**A green suite is not automatically a Survivor.** If the sabotage changed
nothing the Suite could observe, the Mutant is **Inert** and says nothing about
the Suite either. `evaluate_mutant` decides this by running the Record Plan with
and without the Operator, which is why a Record Plan has to be complete.

**Ground truth is confirmed by hand, not by the harness.** `blindspots.json`
records Survivors a human has actually looked at. When measured and confirmed
diverge, the eval says MISMATCH and you investigate — you do not update the
JSON to match.

**A Closing Test is reported only if the Gate passed it.** Green on the clean
Feature, red under the Mutant it claims to close, and green again under every
Benign Change that moves the Feature's output — that third run is what stops the
agent shipping a test that has merely pinned the model's prose. A Benign Change
that changes nothing is Inert and is skipped; a `HARNESS_FAULTS` signature under
one makes that run inconclusive and is never held against the test. The Gate is
in `auditor/agent.py`; it is the reason a small model's assertions are safe to
ship.

**Uplift is measured outside the agent.** `evals/uplift.py` runs it, from the
Closing Tests committed on disk. An agent that scores itself is not evidence.

**Uplift alone can be bought with over-fitting.** A Closing Test that pins the
model's exact prose kills every Mutant and would go red the next time someone
rewords a prompt. `evals/brittleness.py` is the other side of the measurement:
apply a **Benign Change**, and every Closing Test that goes red is a False Alarm.
Never quote Uplift without it — and since the Gate started applying the same
Benign Changes, never quote the False Alarm number as independent evidence
either. It is a regression check on the Gate until a Benign Change is held out.

**Re-recording never deletes.** `record_or_replay` writes fixtures by key and
leaves the old ones, so any change to a prompt orphans everything downstream of
it. Sweep `auditor/fixtures/` after a `--record` — the reachable keys are the
`"kind": "prompt"` events in `trajectories/`. Counting the files instead of the
prompts is how the Changelog once reported the wrong number of model calls.

**Every claim in the submission needs a run behind it.** Ground rule 09.

## Adding a Corpus Case

1. `corpus/NN_name/` with `case.json` (`description`, `tags`, `suite_looks_like`)
2. `feature.py` — expose work through module-level names an Operator can replace
3. `conftest.py` — copy an existing one verbatim; it applies `GREENWASH_MUTATION`
   before pytest imports the tests
4. `tests/test_feature.py` — a suite a real team would plausibly have written.
   No strawmen. Every assertion must be one people actually write.
5. `record_plan.py` — every model call the suite makes
6. `PROMPT_VARIANT` in `feature.py` — the same instruction worded differently,
   for the `prompt.reword` Benign Change. Read both and satisfy yourself they
   mean the same thing; that judgement is the whole basis of the False Alarm
   number
7. Record fixtures for **both** models
8. Run the eval, look at each Survivor by hand, then write `blindspots.json`.
   A Survivor is only a Blind Spot if the sabotage actually changed what the
   Feature returns — the Harness reports the rest as **Inert**, but check the
   observations yourself before recording ground truth:
   `python -m greenwash.observe corpus/NN_name --operator <id>`

`04_purchase_orders` is the **precision control**: a suite that catches
everything, whose `blindspots.json` is deliberately empty. If Greenwash ever
reports a finding there, precision is broken and no other case will tell you.

## Layout

```
greenwash/         operators.py (the sabotage library), harness.py (the loop),
                   modelclient.py (record/replay seam), observe.py (what a
                   Feature actually returned, clean or sabotaged)
corpus/NN_*/       one Corpus Case each
auditor/           agent.py (the Auditor: phases, tools, Verification Gate),
                   audit.py (the CLI and every artifact it writes),
                   fixtures/ (the Auditor's own model answers — replay),
                   closing_tests/, reports/ (Trust Reports), predictions.json
baseline/          the one-shot predictor the Auditor is measured against
evals/run_eval.py  the measurement the Changelog reports against
evals/uplift.py    kill rate before and after Closing Tests — the user's number
evals/brittleness.py  how many Closing Tests fire on output that is correct
evals/score_predictions.py   one scorer, both predictors
selftests/         Greenwash's own tests. Never called a Suite
scripts/           record_fixtures.py, render_trajectory.py
trajectories/      agent traces — required deliverable, capture from run one
docs/adr/          decisions worth their own file
```

## Conventions

Comments explain *why*, at the altitude of the domain — see `greenwash/harness.py`.
Do not narrate what the code plainly does. Match `CONTEXT.md` vocabulary exactly;
if you need a word that is not in it, add it there first.
