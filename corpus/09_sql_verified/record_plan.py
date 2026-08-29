"""Every model call this case's suite makes."""

import feature

CALLS = [lambda q=q: feature.generate(q) for q in ("q1", "q2")]
