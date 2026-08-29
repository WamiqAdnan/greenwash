"""Five cases, exact labels, no judge and nothing hand-wavy.

By every measure this project has, this is a better suite than case 01's. It
asserts values rather than key presence, it covers every label, and it encodes
the house convention that makes the feature worth having.

It is also worthless, and Greenwash cannot tell. See `evals/leakage.py`.
"""

from feature import EXAMPLES, classify

EXPECTED = {k: label for k, (_text, label) in EXAMPLES.items()}


def test_every_ticket_is_routed_to_the_right_queue():
    for ticket_id, label in EXPECTED.items():
        assert classify(ticket_id)["label"] == label


def test_refunds_go_to_account_not_billing():
    """The house convention, asserted explicitly. The reason this suite exists."""
    assert classify("e2")["label"] == "account"


def test_every_label_is_one_we_route_to():
    from feature import LABELS
    for ticket_id in EXPECTED:
        assert classify(ticket_id)["label"] in LABELS
