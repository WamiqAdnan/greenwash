"""Every model call this case's suite makes."""

import feature
from tests.test_feature import QUESTION_IDS

CALLS = [lambda q=q: feature.generate(q) for q in QUESTION_IDS]
