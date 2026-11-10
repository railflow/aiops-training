import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from agent_workflow import TASK_QUEUE, CoverageAgent, decide_activity, tool_activity


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7333"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        worker = Worker(client, task_queue=TASK_QUEUE, workflows=[CoverageAgent], activities=[decide_activity, tool_activity], activity_executor=pool)
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
