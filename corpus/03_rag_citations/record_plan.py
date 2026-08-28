"""Every model call this case's suite makes."""

import feature
from tests.test_feature import QUESTIONS

CALLS = [lambda q=q: feature.answer(q) for q in QUESTIONS]
