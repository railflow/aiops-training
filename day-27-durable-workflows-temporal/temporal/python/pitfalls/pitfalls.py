"""Two ways to break determinism, on purpose. Pick the behaviour with the PITFALL environment variable:

  PITFALL=v1        the "deployed" code: step("a"), wait for the signal "go", step("b")
  PITFALL=v2        the "new release": adds a 1-second sleep BEFORE step("a"). Running workflows already recorded "a" first, so their history no longer matches the code -> non-determinism error
  PITFALL=now       calls datetime.now() inside workflow code -> the sandbox refuses it

Run:  PITFALL=v1 python pitfalls.py worker      then start a workflow, stop the worker, run PITFALL=v2 python pitfalls.py worker, send the signal (or use replay_pitfall.py).
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

PITFALL = os.environ.get("PITFALL", "v1")


@activity.defn
async def step(name: str) -> str:
    return f"ran {name}"


@workflow.defn
class PitfallWorkflow:
    def __init__(self) -> None:
        self._go = False

    @workflow.signal
    def go(self) -> None:
        self._go = True

    @workflow.run
    async def run(self) -> str:
        opts = {"start_to_close_timeout": timedelta(seconds=10)}
        if PITFALL == "now":
            return f"started at {datetime.now()}"  # NOT deterministic: replay would see a different time. Use workflow.now()
        if PITFALL == "v2":
            await workflow.sleep(timedelta(seconds=1))  # a "harmless" 1-second pause added in FRONT of work already recorded
        await workflow.execute_activity(step, "a", **opts)
        await workflow.wait_condition(lambda: self._go)
        return await workflow.execute_activity(step, "b", **opts)


async def main() -> None:
    client = await Client.connect("localhost:7233")
    async with Worker(client, task_queue="pitfalls", workflows=[PitfallWorkflow], activities=[step]):
        print(f"worker running with PITFALL={PITFALL}")
        await asyncio.Event().wait()


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        sys.exit("usage: PITFALL=v1|v2|now python pitfalls.py worker")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
