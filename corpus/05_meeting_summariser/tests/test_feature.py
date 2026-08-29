"""The suite a team writes when the output is prose and nobody wants flaky tests.

Length bounds and a non-emptiness check. It is not lazy — asserting on generated
prose is genuinely hard, and this is the compromise most teams land on. It is
also almost entirely blind.
"""

from feature import read_transcript, summarise

TRANSCRIPTS = ["standup.txt", "pricing.txt"]


def test_a_summary_comes_back():
    for name in TRANSCRIPTS:
        assert summarise(name).strip()


def test_the_summary_is_shorter_than_the_transcript():
    for name in TRANSCRIPTS:
        assert len(summarise(name)) < len(read_transcript(name))


def test_the_summary_is_not_a_stub():
    """Guards against the model returning "OK" or an empty string."""
    for name in TRANSCRIPTS:
        assert len(summarise(name)) > 120
