"""Every model call this case's suite makes, so replay never misses a fixture."""

import feature

CALLS = [
    lambda: feature.extract("po_1.txt"),
    lambda: feature.extract("po_2.txt"),
]
