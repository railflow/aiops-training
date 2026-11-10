"""Replay a recorded PitfallWorkflow history against the code selected by PITFALL. This is how you catch a breaking change BEFORE deploying.

  temporal workflow show -w pitfall-3 --output json > pitfall-history.json
  PITFALL=v1 python replay_pitfall.py pitfall-3 pitfall-history.json     # OK
  PITFALL=v2 python replay_pitfall.py pitfall-3 pitfall-history.json     # non-determinism error
"""
import asyncio
import sys
from pathlib import Path

from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer

from pitfalls import PITFALL, PitfallWorkflow


async def main(workflow_id: str, path: str) -> None:
    history = WorkflowHistory.from_json(workflow_id, Path(path).read_text())
    await Replayer(workflows=[PitfallWorkflow]).replay_workflow(history)
    print(f"replay OK with PITFALL={PITFALL}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
