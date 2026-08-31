# Trust Report — 12_agent_loop

**The feature.** Answers a customer question by calling tools in a loop until it has an answer.

**The suite.** Checks the loop terminates, stays inside its step budget, calls at least one tool and returns a non-empty answer. Never checks that the answer follows from what the tools returned.

**Kill rate: 60%** — 3 of 5 sabotages were noticed.

2 ways this feature can break without your suite going red. Every one below was applied to the real feature and the suite was run; it stayed green.

0 of them now have a test that would have caught it.

## `agent.answer_ignores_tools`

The agent replies with a confident summary that does not use what the tools returned.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. red on the clean feature (assertion failed)
2. red on the clean feature (assertion failed)
3. red on the clean feature (assertion failed)

## `agent.gives_up_quietly`

The agent stops after its first step and returns a holding reply.

- suite under this sabotage: **suite stayed green**
- **no closing test.** 3 attempt(s), last verdict: red on the clean feature (assertion failed)

This one is still open. The blind spot is real — the run above proves it — but the auditor could not write a test that closed it.

Rejected by the gate along the way:

1. red on the clean feature (assertion failed)
2. false alarm: the feature still works under model.pin_previous and the test went red anyway
3. red on the clean feature (assertion failed)

## What the auditor expected, before it ran anything

Predicted misses: `agent.answer_ignores_tools`, `agent.gives_up_quietly`

Actually missed: `agent.answer_ignores_tools`, `agent.gives_up_quietly`

> The suite does not verify the correctness of the final answer, only that an answer was provided and the loop terminated.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
