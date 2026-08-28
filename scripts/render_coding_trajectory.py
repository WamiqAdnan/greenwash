#!/usr/bin/env python
"""Render a Claude Code session into a readable coding-agent trajectory.

The hackathon asks for representative trajectories for *every* agent used, and
this repository was built by one. Its traces already exist on disk, written as
the work happened, so this renders them rather than reconstructing anything.

    python scripts/render_coding_trajectory.py ~/.claude/projects/<slug>/<id>.jsonl \\
        -o trajectories/building-greenwash-2-the-auditor.md

Conservative by default, because these traces are published:

  - `<system-reminder>` blocks are dropped — harness plumbing, not agent work
  - email addresses are redacted
  - tool results are truncated; the point is what came back, not all of it
  - the agent's private reasoning is excluded unless --include-thinking
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>\s*", re.S)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
HOME = re.compile(r"/Users/[^/\s]+")


def clean(text: str) -> str:
    text = REMINDER.sub("", text or "")
    text = EMAIL.sub("<redacted@example.com>", text)
    return HOME.sub("~", text)


def truncate(text: str, limit: int) -> str:
    text = text.rstrip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n… [{len(text) - limit} more characters]"


def fence(text: str, lang: str = "") -> list[str]:
    ticks = "`" * max(3, _longest_run(text) + 1)
    return [f"{ticks}{lang}", text.rstrip(), ticks, ""]


def _longest_run(text: str) -> int:
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return longest


def blocks(message) -> list:
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content or []


def render(path: Path, title: str, limit: int, thinking: bool) -> str:
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    out = [
        f"# Trajectory — coding agent: {title}",
        "",
        "The agent that built this repository, traced from the session log it "
        "wrote while working.",
        "",
        f"- source: `{path.name}` ({len(records)} records)",
        "- system reminders removed, home directory and email addresses redacted",
        f"- tool results truncated to {limit} characters",
        f"- private reasoning: {'included' if thinking else 'excluded'}",
        "",
        "---",
        "",
    ]
    step = 0
    for record in records:
        kind = record.get("type")
        if kind not in ("user", "assistant"):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        for block in blocks(message):
            btype = block.get("type")
            if btype == "text":
                text = clean(block.get("text", ""))
                if not text.strip():
                    continue
                step += 1
                who = "the human asked" if kind == "user" else "the agent said"
                out += [f"### {step}. {who}", ""] + fence(truncate(text, limit * 3))
            elif btype == "thinking" and thinking:
                step += 1
                out += [f"### {step}. the agent thought", ""]
                out += fence(truncate(clean(block.get("thinking", "")), limit))
            elif btype == "tool_use":
                step += 1
                args = json.dumps(block.get("input", {}))[:600]
                out += [f"### {step}. the agent ran `{block.get('name')}`", ""]
                out += fence(clean(args), "json")
            elif btype == "tool_result":
                content = block.get("content")
                if isinstance(content, list):
                    content = "\n".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                text = clean(str(content or ""))
                if not text.strip():
                    continue
                step += 1
                out += [f"### {step}. the tool responded", ""]
                out += fence(truncate(text, limit))
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--title", default="building Greenwash")
    ap.add_argument("--limit", type=int, default=1200,
                    help="characters kept per tool result")
    ap.add_argument("--include-thinking", action="store_true")
    args = ap.parse_args()

    args.out.write_text(
        render(args.session, args.title, args.limit, args.include_thinking)
    )
    size = args.out.stat().st_size
    print(f"wrote {args.out} ({size // 1024} KB)")


if __name__ == "__main__":
    main()
