"""The coverage agent as a Temporal workflow (Python SDK). Same scenario, same scripted model, same tools as the Eve lab.

The agent loop is the workflow function. Everything that touches the outside world (the model call, each tool) is an
activity. The approval gate is a signal and a durable wait. Nothing here is specific to AI: it is the Day 27 pattern.
"""
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import lab_common as lab

TASK_QUEUE = "coverage-agent"
APPROVAL_TIMEOUT = timedelta(hours=4)


@activity.defn
def decide_activity(task: str, results: list[tuple[str, bool]]) -> dict:
    """Stands in for the model call: a real LLM call belongs in an activity so its result is recorded."""
    return lab.decide(task, results)


@activity.defn
def tool_activity(tool: str, args: dict) -> dict:
    return lab.TOOLS[tool](**args)


@workflow.defn
class CoverageAgent:
    def __init__(self) -> None:
        self.decision: str | None = None
        self.waiting_for_approval = False

    @workflow.signal
    def approve(self, decision: str) -> None:
        self.decision = decision

    @workflow.query
    def state(self) -> dict:
        return {"waiting_for_approval": self.waiting_for_approval, "decision": self.decision}

    @workflow.run
    async def run(self, task: str) -> str:
        results: list[tuple[str, bool]] = []
        while True:
            step = await workflow.execute_activity(decide_activity, args=[task, results], start_to_close_timeout=timedelta(seconds=30))
            if "text" in step:
                return step["text"]
            tool = step["tool"]
            if tool == "open_pr":
                self.waiting_for_approval, self.decision = True, None
                try:
                    await workflow.wait_condition(lambda: self.decision is not None, timeout=APPROVAL_TIMEOUT)
                except TimeoutError:
                    return "stopped: approval timed out"
                finally:
                    self.waiting_for_approval = False
                if self.decision != "approve":
                    return "stopped: pull request not approved"
            await workflow.execute_activity(
                tool_activity, args=[tool, step["args"]],
                # A worker that dies mid-activity is noticed when this timeout passes; the retry runs on any worker.
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5),
            )
            results.append((tool, False))
