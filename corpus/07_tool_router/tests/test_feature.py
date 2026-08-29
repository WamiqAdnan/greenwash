"""The suite that grew up alongside the router.

It checks the right tool fires, which is what went wrong in early testing and
what everyone therefore wrote tests for. The arguments were always right, so
nobody wrote a test for them.
"""

from feature import TOOLS, route

EXPECTED_TOOL = {
    "r1": "issue_refund",
    "r2": "update_address",
    "r3": "escalate_to_human",
}


def test_the_right_tool_is_chosen():
    for request_id, tool in EXPECTED_TOOL.items():
        assert route(request_id)["tool"] == tool


def test_the_tool_is_one_that_exists():
    names = {t["name"] for t in TOOLS}
    for request_id in EXPECTED_TOOL:
        assert route(request_id)["tool"] in names


def test_arguments_are_supplied():
    for request_id in EXPECTED_TOOL:
        assert isinstance(route(request_id)["arguments"], dict)
