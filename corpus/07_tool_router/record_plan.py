"""Every model call this case's suite makes."""

import feature
from tests.test_feature import EXPECTED_TOOL

CALLS = [lambda r=r: feature.route(r) for r in EXPECTED_TOOL]
