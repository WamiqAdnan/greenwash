"""Every model call this case's suite makes."""

import feature
from tests.test_feature import OBVIOUS

CALLS = [lambda p=p: feature.moderate(p) for p in OBVIOUS]
