"""The suite written from the examples in the policy document.

Obvious abuse, obvious spam, obvious fine. Everything a reviewer would agree on
without discussion — which is exactly why nobody argued about the test cases,
and exactly why there are no hard ones.
"""

from feature import moderate

OBVIOUS = {"p1": True, "p2": False, "p3": True}


def test_obvious_cases_are_decided_correctly():
    for post_id, expected in OBVIOUS.items():
        assert moderate(post_id)["flagged"] is expected


def test_a_category_comes_back():
    for post_id in OBVIOUS:
        assert isinstance(moderate(post_id)["category"], str)


def test_clean_content_is_not_flagged():
    assert moderate("p2")["flagged"] is False
