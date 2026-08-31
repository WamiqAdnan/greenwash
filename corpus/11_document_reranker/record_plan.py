"""Every model call this case's suite makes."""

import feature

CALLS = [lambda q=q: feature.rank(q) for q in feature.QUERIES]
