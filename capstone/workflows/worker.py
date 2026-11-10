"""The capstone worker. Settings from the environment (see k8s/40-worker-deployment.yaml). Sync activities run in a thread pool (they block on kubectl)."""
import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "measure"))
import ship  # noqa: E402
from flow_activities import Activities, all_activities  # noqa: E402
from flow_runners import KubernetesJobRunner  # noqa: E402
from flow_workflows import FixIssueWorkflow, ImproveFleetWorkflow, ImproveRepoWorkflow, MeasureRepoWorkflow  # noqa: E402
from forge import ForgejoApi  # noqa: E402


async def main():
    logging.basicConfig(level=logging.INFO)
    e = os.environ
    client = await Client.connect(e.get("TEMPORAL_ADDRESS", "localhost:7233"), namespace=e.get("TEMPORAL_NAMESPACE", "default"))
    forge = ForgejoApi(e["FORGEJO_URL"], e.get("FORGEJO_ADMIN_TOKEN", ""), e.get("FORGEJO_BOT_USER", "agent-bot"), e.get("FORGEJO_BOT_PASSWORD", "")) if e.get("FORGEJO_URL") else None
    acts = Activities(KubernetesJobRunner(e.get("NAMESPACE", "capstone")), lambda table, rows: ship.insert_rows(rows, table=table), forge)
    async with Worker(client, task_queue=e.get("TASK_QUEUE", "capstone"),
                      workflows=[ImproveRepoWorkflow, ImproveFleetWorkflow, MeasureRepoWorkflow, FixIssueWorkflow], activities=all_activities(acts),
                      activity_executor=ThreadPoolExecutor(8), max_concurrent_activities=int(e.get("MAX_ACTIVITIES", "4"))):    # LAPTOP: this is also a concurrency cap
        logging.info("capstone worker running")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
