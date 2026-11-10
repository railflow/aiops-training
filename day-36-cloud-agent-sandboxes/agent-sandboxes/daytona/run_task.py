"""Run the common task on Daytona. From day-36-cloud-agent-sandboxes/agent-sandboxes: python daytona/run_task.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.real import main  # noqa: E402

raise SystemExit(main("daytona"))
