"""A tool-using agent loop — the feature under test.

Answers a customer question by calling tools until it has enough to reply. The
loop is the ordinary one: ask the model what to do, do it, show it the result,
ask again. What the customer receives is the answer at the end.
"""

from __future__ import annotations

import json
import re

from greenwash.modelclient import complete

MAX_STEPS = 4

ORDERS = {
    "A-4471": "shipped on 2026-03-16, tracking DX99210, delivered 2026-03-18",
}

STOCK = {
    "DM-12": "0 units on hand, next delivery expected 2026-04-09",
}

TOOLS = [
    {"name": "lookup_order", "arguments": ["order_id"]},
    {"name": "check_stock", "arguments": ["sku"]},
]

TASKS = {
    "t1": "Has order A-4471 shipped yet?",
    "t2": "Do we have SKU DM-12 in stock right now?",
}

PROMPT = """You are answering a customer question. You may call a tool, or give
the final answer if you already have what you need.

Tools:
{tools}

Question: {task}

What has happened so far:
{trace}

Reply with JSON only. To call a tool: {{"tool": "...", "arguments": {{...}}}}
To finish: {{"answer": "..."}}

JSON:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Answer the customer's question below. You can either call one
of the tools or, if you already know enough, reply with the final answer.

Tools:
{tools}

Question: {task}

Steps taken so far:
{trace}

Respond with JSON only. A tool call looks like
{{"tool": "...", "arguments": {{...}}}} and a final answer looks like
{{"answer": "..."}}.

JSON:"""


def _catalogue() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['arguments'])})" for t in TOOLS)


def _render(trace: list[dict]) -> str:
    if not trace:
        return "(nothing yet)"
    return "\n".join(
        f"called {s['tool']}({json.dumps(s['arguments'])}) -> {s['observation']}"
        for s in trace
    )


def run_tool(name: str, arguments: dict) -> str:
    """Execute one tool call and return what it saw."""
    if name == "lookup_order":
        return ORDERS.get(arguments.get("order_id", ""), "no such order")
    if name == "check_stock":
        return STOCK.get(arguments.get("sku", ""), "no such sku")
    return f"no such tool: {name}"


def solve(task_id: str) -> dict:
    """Work the task until there is an answer, and report what was done."""
    trace: list[dict] = []
    for _ in range(MAX_STEPS):
        raw = complete(PROMPT.format(
            tools=_catalogue(), task=TASKS[task_id], trace=_render(trace)
        ))
        step = _parse(raw)
        if "answer" in step:
            return {"answer": step["answer"], "steps": trace, "terminated": True}
        name = step.get("tool", "")
        arguments = step.get("arguments", {})
        trace.append({
            "tool": name,
            "arguments": arguments,
            "observation": run_tool(name, arguments),
        })
    return {"answer": "", "steps": trace, "terminated": False}


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        # A real loop does not crash because one reply was prose; it takes the
        # reply as the answer and stops. That this is indistinguishable from a
        # good answer, to a suite that checks only that a string came back, is
        # the point of this Corpus Case.
        return {"answer": raw.strip()}
    return json.loads(match.group(0))
