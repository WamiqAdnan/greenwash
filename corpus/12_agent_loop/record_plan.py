"""Every model call this case's suite makes.

One entry per task: `solve` runs the loop, so a single call here is however many
model calls that task takes.
"""

import feature

CALLS = [lambda t=t: feature.solve(t) for t in feature.TASKS]
