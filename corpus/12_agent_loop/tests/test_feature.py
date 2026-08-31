"""The suite that grew up alongside the agent loop.

The loop's early failures were all liveness: it looped forever, it blew the step
budget, it came back with nothing. So the team tested liveness, and every
assertion below is one that a real agent suite has. What none of them ask is
whether the answer is true — that needs a judgement about the observations, and
"it finished" is so much easier to write.
"""

from feature import MAX_STEPS, TASKS, TOOLS, solve


def test_the_loop_terminates():
    for task_id in TASKS:
        assert solve(task_id)["terminated"] is True


def test_it_does_not_run_away():
    for task_id in TASKS:
        assert len(solve(task_id)["steps"]) <= MAX_STEPS


def test_it_actually_did_some_work():
    for task_id in TASKS:
        assert solve(task_id)["steps"], "the agent answered without calling anything"


def test_there_is_a_final_answer():
    for task_id in TASKS:
        answer = solve(task_id)["answer"]
        assert isinstance(answer, str) and answer.strip()


def test_the_trace_is_well_formed():
    names = {t["name"] for t in TOOLS}
    for task_id in TASKS:
        for step in solve(task_id)["steps"]:
            assert set(step) == {"tool", "arguments", "observation"}
            assert step["tool"] in names
            assert isinstance(step["arguments"], dict)
