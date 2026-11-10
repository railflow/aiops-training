"""Start (or find) a MonthlyTaxProcessingWorkflow from code. Same job as the CLI, with typed input.

  python starter.py BATCH-2026-11 [--cooling-off 20] [--wait]

The Workflow ID is deterministic (monthly-tax-<batch>), so running this twice for the same batch cannot start two batches:
the second call attaches to the one already running. That is your idempotency key for "start".
"""
import argparse
import asyncio
import os

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from models import BatchInput
from workflow import MonthlyTaxProcessingWorkflow


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("batch_id")
    p.add_argument("--cooling-off", type=int, default=86400, help="seconds")
    p.add_argument("--approval-timeout-hours", type=int, default=72)
    p.add_argument("--wait", action="store_true", help="block until the workflow finishes and print the result")
    a = p.parse_args()

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"), namespace=os.environ.get("TEMPORAL_NAMESPACE", "default")
    )
    handle = await client.start_workflow(
        MonthlyTaxProcessingWorkflow.run,
        BatchInput(a.batch_id, a.cooling_off, a.approval_timeout_hours),
        id=f"monthly-tax-{a.batch_id}",
        task_queue=os.environ.get("TASK_QUEUE", "enterprise-batch-queue"),
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
    print(f"workflow_id={handle.id} run_id={handle.result_run_id}")
    if a.wait:
        print(await handle.result())


if __name__ == "__main__":
    asyncio.run(main())
