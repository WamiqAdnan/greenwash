"""Closing Tests the Auditor wrote for 05_meeting_summariser.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-05_meeting_summariser.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""


# closes: model.echo — The model is replaced by one that echoes its input back.
# gate: green on the clean feature, red under model.echo, green under prompt.reword
# fails as: FAILED tests/test_greenwash_closing.py::test_summary_contains_key_decisions
from feature import read_transcript, summarise

def test_summary_contains_key_decisions():
    standup = summarise("standup.txt")
    pricing = summarise("pricing.txt")
    assert "exponential backoff" in standup and "Kafka upgrade" in standup
    assert "starter tier price" in pricing and "discount experiment" in pricing
