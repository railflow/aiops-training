"""Replay a recorded history against the CURRENT workflow code. If you changed the code in a way that breaks running workflows,
this raises a non-determinism error here, in a test or CI step, instead of in production.

  temporal workflow show --workflow-id monthly-tax-BATCH-2026-11 --output json > history.json
  python replay.py monthly-tax-BATCH-2026-11 history.json
"""
import asyncio
import sys
from pathlib import Path

from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer

from workflow import MonthlyTaxProcessingWorkflow


async def main(workflow_id: str, path: str) -> None:
    history = WorkflowHistory.from_json(workflow_id, Path(path).read_text())
    await Replayer(workflows=[MonthlyTaxProcessingWorkflow]).replay_workflow(history)
    print("replay OK: the current code is compatible with this history")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: replay.py WORKFLOW_ID HISTORY_JSON")
    asyncio.run(main(sys.argv[1], sys.argv[2]))
