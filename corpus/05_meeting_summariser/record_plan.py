"""Every model call this case's suite makes."""

import feature
from tests.test_feature import TRANSCRIPTS

CALLS = [lambda n=n: feature.summarise(n) for n in TRANSCRIPTS]
