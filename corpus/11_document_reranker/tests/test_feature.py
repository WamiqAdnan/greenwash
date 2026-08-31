"""The suite that grew up alongside the re-ranker.

Relevance needs labelled data and nobody had any, so the team tested the thing
they could state exactly: that the ranker hands back the documents it was given,
each of them once, and nothing it invented. Every assertion here is one a real
team writes on the first day of having a ranker.
"""

from feature import DOCUMENTS, QUERIES, rank


def test_every_document_comes_back():
    for query_id in QUERIES:
        assert set(rank(query_id)) == set(DOCUMENTS)


def test_no_document_is_repeated():
    for query_id in QUERIES:
        ranking = rank(query_id)
        assert len(ranking) == len(set(ranking))


def test_the_ranking_covers_the_whole_corpus():
    for query_id in QUERIES:
        assert len(rank(query_id)) == len(DOCUMENTS)


def test_nothing_is_invented():
    for query_id in QUERIES:
        assert all(doc_id in DOCUMENTS for doc_id in rank(query_id))
