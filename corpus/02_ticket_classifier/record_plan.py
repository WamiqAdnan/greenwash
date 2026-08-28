"""Every model call this case's suite makes — the feature's and the judge's."""

import feature
from greenwash.modelclient import complete

import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])


def _judge_calls():
    from tests.test_feature import JUDGE
    for label in feature.LABELS:
        complete(JUDGE.format(label=label))


CALLS = [
    lambda: feature.classify("t1"),
    lambda: feature.classify("t2"),
    lambda: feature.classify("t3"),
    _judge_calls,
]
