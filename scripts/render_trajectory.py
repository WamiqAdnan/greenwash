#!/usr/bin/env python
"""Turn a Trajectory into something a person can read start to finish.

A required deliverable asks for traces that are easy to follow from the agent's
instructions to its final result, including the feedback that shaped each next
step. JSONL is the right thing to write while the agent works and the wrong
thing to hand a reviewer, so this renders one into Markdown.

    python scripts/render_trajectory.py trajectories/audit-01_invoice_extractor.jsonl
    python scripts/render_trajectory.py --all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAJECTORIES = ROOT / "trajectories"

PHASE_HEADINGS = {
    "triage": "Phase 1 — triage: read the case, order the sabotages, record a prior",
    "verify": "Phase 2 — verify: apply each sabotage, run the suite, read the result",
    "remediate": "Phase 3 — remediate: write a test per survivor, and prove it works",
    "report": "Phase 4 — report",
}


def fence(text: str, lang: str = "") -> list[str]:
    """A model answer often arrives already fenced, so ours has to be longer."""
    ticks = "`" * max(3, _longest_run(text) + 1)
    return [f"{ticks}{lang}", text.rstrip(), ticks, ""]


def _longest_run(text: str) -> int:
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return longest


def render(path: Path) -> str:
    events = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    header = events[0]
    out = [
        f"# Trajectory — {header.get('agent')} on {header.get('case')}",
        "",
        f"- model: `{header.get('model')}` ({header.get('mode')} mode)",
        f"- tools: {', '.join(f'`{t}`' for t in header.get('tools', []))}",
        f"- closing-test attempts allowed per survivor: {header.get('max_attempts')}",
        f"- operator budget: {header.get('budget') or 'none (whole applicable catalogue)'}",
        "",
        "## The agent's instructions",
        "",
        *fence(header.get("instructions", "")),
    ]

    seen_phase = None
    for e in events[1:]:
        if e["phase"] != seen_phase:
            seen_phase = e["phase"]
            out += ["", f"## {PHASE_HEADINGS.get(seen_phase, seen_phase)}", ""]

        kind, step = e["kind"], e["step"]
        if kind == "tool_call":
            args = {k: v for k, v in e.get("args", {}).items() if k != "code"}
            out.append(f"**{step}. tool call** `{e['tool']}({_args(args)})`")
            if "code" in e.get("args", {}):
                out += ["", "the test it is asking the gate to judge:", ""]
                out += fence(e["args"]["code"], "python")
            out.append("")
        elif kind == "tool_result":
            out += [f"**{step}. {e['tool']} responded**", ""] + fence(e.get("text", ""))
        elif kind == "prompt":
            out += [f"**{step}. asked `{e.get('model')}`**", "",
                    "<details><summary>full prompt</summary>", ""]
            out += fence(e.get("text", ""))
            out += ["</details>", ""]
        elif kind == "response":
            out += [f"**{step}. `{e.get('model')}` answered**", ""]
            out += fence(e.get("text", ""))
        elif kind == "decision":
            out += [f"**{step}. recorded prior** (evidence, never a finding)", ""]
            out += fence(json.dumps(e.get("prior", {}), indent=2), "json")
        elif kind == "findings":
            out += [f"**{step}. result**", ""]
            out += fence(json.dumps(
                {k: v for k, v in e.items() if k not in ("step", "phase", "kind")},
                indent=2), "json")
    return "\n".join(out) + "\n"


def _args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("trajectory", type=Path, nargs="?")
    ap.add_argument("--all", action="store_true", help="render every trajectory")
    args = ap.parse_args()

    paths = sorted(TRAJECTORIES.glob("*.jsonl")) if args.all else [args.trajectory]
    if not paths or paths == [None]:
        raise SystemExit("give a trajectory path, or --all")
    for path in paths:
        out = path.with_suffix(".md")
        out.write_text(render(path))
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
