"""Closing Tests the Auditor wrote for 10_few_shot_leak.

Each one passed the Verification Gate: green on the clean feature, red
under the Operator named above it, and green again under every benign
change that moves this feature's output — the `gate:` line on each test
says which. Written by `auditor/audit.py`; the reasoning and the
rejected attempts are in
`trajectories/audit-10_few_shot_leak.jsonl`.

Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.
"""
