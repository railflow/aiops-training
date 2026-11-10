"""Run the common task on Modal. From day-36-cloud-agent-sandboxes/agent-sandboxes: python modal/run_task.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.real import main  # noqa: E402

raise SystemExit(main("modal"))
