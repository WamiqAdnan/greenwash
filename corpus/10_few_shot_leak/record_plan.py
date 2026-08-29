"""Every model call this case's Suite makes, and the ones only the probe makes.

`CALLS` is the Record Plan proper: the five in-prompt examples, which are exactly
what the Suite tests. The Inert check compares these with and without an
Operator, so keeping the held-out tickets out of it is what keeps "the Suite
could not have noticed" a true statement rather than a convenient one.

`EXTRA_CALLS` is recorded and never observed — `evals/leakage.py` replays it.
"""

import feature

CALLS = [lambda t=t: feature.classify(t) for t in feature.EXAMPLES]

EXTRA_CALLS = [lambda t=t: feature.classify(t) for t in feature.HELDOUT]
