# Agent trajectories

Two agents were used on this project, and both are traced here.

## The Auditor — the agent that is the submission

`audit-<case>.jsonl` is written *while the agent works*, one JSON object per
event, by `auditor/agent.py`. `audit-<case>.md` is the same trace rendered for
reading, by `scripts/render_trajectory.py`.

Each trace opens with the agent's own instructions and the tools it was given,
then runs in order:

| Phase | What you are looking at |
|---|---|
| triage | it reads the feature and the suite, orders the sabotages, and records a **prior** — what it expects to survive, before anything has run |
| verify | one sabotage per step, applied for real; the tool result is the suite's actual output |
| remediate | one closing test per survivor, judged by the Verification Gate; **rejections and retries are in here**, with the pytest output the agent was shown |
| report | what it ended up claiming |

The prior in phase 1 is the interesting part to read against phase 2. It is
recorded as evidence and never reported as a finding.

These files are timestamp-free on purpose: replaying a recorded audit
(`auditor/audit.py`, no flags) rewrites them byte for byte, so `git diff` after
a reproduction run is empty if the reproduction is faithful.

## The coding agent — how the project was built

`building-greenwash-*.md` are traces of the coding agent used to build this
repository, with the same structure: what it was asked, what it ran, what came
back, and what it did next.
