#!/usr/bin/env python
"""Run the Auditor over the corpus and write everything it is judged on.

    .venv/bin/python auditor/audit.py                  # replay, offline, no Ollama
    .venv/bin/python auditor/audit.py --record         # talks to Ollama, rewrites fixtures
    .venv/bin/python auditor/audit.py --case 03_rag_citations -v

Outputs, all committed so a judge can read them without running anything:

    auditor/predictions.json          the contract, scored by evals/score_predictions.py
    auditor/prior_predictions.json    what it expected before running, same scorer
    auditor/closing_tests/<case>.py   the tests that close what survived
    auditor/reports/<case>.md         the Trust Report — what the user actually reads
    auditor/audit.json               every finding with its receipt and its Prior
    trajectories/audit-<case>.jsonl   the trace, written as the agent worked

The Kill Rate after Closing Tests is deliberately NOT computed here. The agent
does not score itself; `evals/uplift.py` does that.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auditor import agent  # noqa: E402
from greenwash import harness  # noqa: E402

PREDICTOR = "auditor-v1"
FIXTURES = ROOT / "auditor" / "fixtures"
REPORTS = ROOT / "auditor" / "reports"
CLOSING = ROOT / "auditor" / "closing_tests"
TRAJECTORIES = ROOT / "trajectories"


def slug(operator_id: str) -> str:
    return re.sub(r"\W+", "_", operator_id)


def closing_test_module(case_name: str, findings: list[agent.Finding]) -> str:
    """One file per Corpus Case, every test in it already through the Gate."""
    closed = [f for f in findings if f.closed]
    parts = [
        f'"""Closing Tests the Auditor wrote for {case_name}.\n\n'
        f"Each one passed the Verification Gate: green on the clean feature, red\n"
        f"under the Operator named above it. Written by `auditor/audit.py`; the\n"
        f"reasoning and the rejected attempts are in\n"
        f"`trajectories/audit-{case_name}.jsonl`.\n\n"
        f"Merged onto an Overlay by `evals/uplift.py`. Never written into a Suite.\n"
        f'"""\n'
    ]
    used: set[str] = set()
    for f in closed:
        code = f.closing_test
        for name in re.findall(r"def (test_\w+)", code):
            if name in used:
                code = code.replace(f"def {name}", f"def {name}__{slug(f.operator)}")
                used.add(f"{name}__{slug(f.operator)}")
            else:
                used.add(name)
        parts.append(
            f"# closes: {f.operator} — {f.summary}\n"
            f"# gate: {f.gate}\n"
            f"# fails as: {f.closing_test_failure}\n"
            f"{code.strip()}\n"
        )
    return "\n\n".join(parts)


def trust_report(case: harness.Case, result: agent.AuditResult) -> str:
    """The deliverable, not a log. Written for the engineer who owns the feature."""
    closed = [f for f in result.findings if f.closed]
    lines = [
        f"# Trust Report — {case.name}",
        "",
        f"**The feature.** {case.description}",
        "",
        f"**The suite.** {case.suite_looks_like}",
        "",
        f"**Kill rate: {result.kill_rate_before:.0%}** — "
        f"{len(result.killed)} of {len(result.killed) + len(result.findings)} "
        f"sabotages were noticed.",
        "",
    ]
    if result.findings:
        lines += [
            f"{len(result.findings)} ways this feature can break without your suite "
            f"going red. Every one below was applied to the real feature and the "
            f"suite was run; it stayed green.",
            "",
            f"{len(closed)} of them now {'has' if len(closed) == 1 else 'have'} "
            f"a test that would have caught it.",
            "",
        ]
    else:
        lines += ["No sabotage survived this suite.", ""]

    for f in result.findings:
        lines += [
            f"## `{f.operator}`",
            "",
            f"{f.summary}",
            "",
            f"- suite under this sabotage: **{f.receipt}**",
        ]
        if f.closed:
            lines += [
                f"- closing test: verified {f.gate}",
                f"- it fails as: `{f.closing_test_failure}`",
                f"- attempts needed: {f.attempts}",
                "",
                "```python",
                f.closing_test.strip(),
                "```",
                "",
            ]
        else:
            lines += [
                f"- **no closing test.** {f.attempts} attempt(s), last verdict: "
                f"{f.gate}",
                "",
                "This one is still open. The blind spot is real — the run above "
                "proves it — but the auditor could not write a test that closed it.",
                "",
            ]

    if result.inert:
        lines += [
            "## Tried, and nothing happened",
            "",
            "These sabotages were applied and your feature returned exactly what "
            "it returned before. Your suite stayed green because there was "
            "nothing to notice — this is not a hole:",
            "",
            *[f"- `{op}`" for op in result.inert],
            "",
        ]
    if result.invalid:
        lines += [
            "## Not measured",
            "",
            "These sabotages could not be run, so they say nothing about your "
            "suite either way:",
            "",
            *[f"- `{op}`" for op in result.invalid],
            "",
        ]
    if result.skipped:
        lines += [
            "## Not run (budget)",
            "",
            *[f"- `{op}`" for op in result.skipped],
            "",
        ]

    prior = result.prior
    lines += [
        "## What the auditor expected, before it ran anything",
        "",
        f"Predicted misses: {', '.join(f'`{x}`' for x in prior['expect_missed']) or '(none)'}",
        "",
        f"Actually missed: {', '.join(f'`{x}`' for x in result.survivors) or '(none)'}",
        "",
        f"> {prior['why'] or '(no reason given)'}",
        "",
        "The prediction is kept as evidence and never reported as a finding. "
        "Findings come from runs.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--case", help="audit a single case by directory name")
    ap.add_argument("--record", action="store_true",
                    help="call Ollama and rewrite the auditor's fixtures")
    ap.add_argument("--max-attempts", type=int, default=3,
                    help="closing-test attempts per survivor before giving up")
    ap.add_argument("--budget", type=int,
                    help="run only this many operators per case, in the order "
                         "the auditor chose")
    ap.add_argument("-o", "--out", type=Path,
                    default=ROOT / "auditor" / "predictions.json")
    args = ap.parse_args()

    cases = harness.discover()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            raise SystemExit(f"no such case: {args.case}")

    mode = "record" if args.record else "replay"
    for d in (REPORTS, CLOSING, TRAJECTORIES, FIXTURES):
        d.mkdir(parents=True, exist_ok=True)

    results: list[agent.AuditResult] = []
    for case in cases:
        print(f"\n{case.name}  [{', '.join(sorted(case.tags))}]")
        trajectory = agent.Trajectory(
            TRAJECTORIES / f"audit-{case.name}.jsonl",
            {
                "agent": PREDICTOR,
                "case": case.name,
                "model": args.model,
                "mode": mode,
                "instructions": agent.INSTRUCTIONS,
                "tools": ["read_feature", "read_suite", "list_operators", "observe",
                          "run_operator", "propose_closing_test"],
                "max_attempts": args.max_attempts,
                "budget": args.budget,
            },
        )
        model = agent.Model(args.model, FIXTURES, mode, trajectory)
        result = agent.audit_case(
            case, model, trajectory,
            max_attempts=args.max_attempts, budget=args.budget,
        )
        results.append(result)

        (CLOSING / f"{case.name}.py").write_text(
            closing_test_module(case.name, result.findings)
        )
        (REPORTS / f"{case.name}.md").write_text(trust_report(case, result))
        closed = sum(f.closed for f in result.findings)
        print(f"  kill rate before: {result.kill_rate_before:.0%}   "
              f"blind spots: {len(result.findings)}   closed: {closed}")

    args.out.write_text(json.dumps(
        {
            "predictor": PREDICTOR,
            "model": args.model,
            "verified": True,
            "predictions": {r.case: r.survivors for r in results},
            # Structurally zero: a finding is an Operator that was run, so the
            # Auditor cannot name one that does not exist.
            "hallucinated_ids": {r.case: [] for r in results},
            "closed": {r.case: [f.operator for f in r.findings if f.closed]
                       for r in results},
            "prior": {r.case: r.prior for r in results},
        },
        indent=2,
    ))
    # The Prior, in the same shape and scored by the same scorer. Same model,
    # same case, same question — the only difference is that the Prior was not
    # allowed to run anything. That is the experiment this project is about, and
    # every audit re-runs it for free.
    (ROOT / "auditor" / "prior_predictions.json").write_text(json.dumps(
        {
            "predictor": "auditor-v1-prior",
            "model": args.model,
            "verified": False,
            "predictions": {r.case: r.prior["expect_missed"] for r in results},
            "hallucinated_ids": {r.case: r.prior["invented_ids"] for r in results},
            "note": "what the auditor expected before it ran anything. Evidence, "
                    "never a finding — see docs/adr/0001.",
        },
        indent=2,
    ))
    (ROOT / "auditor" / "audit.json").write_text(json.dumps(
        [asdict(r) | {"kill_rate_before": round(r.kill_rate_before, 4)}
         for r in results], indent=2,
    ))
    total_found = sum(len(r.findings) for r in results)
    total_closed = sum(f.closed for r in results for f in r.findings)
    print(f"\n{total_found} blind spots, {total_closed} closed")
    print(f"wrote {args.out}")
    print("wrote auditor/prior_predictions.json — what it expected, "
          "scored by the same scorer")


if __name__ == "__main__":
    main()
