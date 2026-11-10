"""A human gate before the irreversible step (opening a pull request). The policy is yours with or without a framework."""
import time
from pathlib import Path


# >> C17 human approval
def approval(mode: str, repo: str, wait_s: float = 0.0, sleep=time.sleep) -> str:
    """Returns 'approved', 'denied' or 'pending'. mode: auto | deny | file:PATH (PATH lists one approved repo per line)."""
    if mode == "auto":
        return "approved"
    if mode == "deny":
        return "denied"
    path, deadline = Path(mode.removeprefix("file:")), time.monotonic() + wait_s
    while True:
        if path.exists() and repo in path.read_text().split():
            return "approved"
        if time.monotonic() >= deadline:
            return "pending"
        sleep(min(1.0, wait_s))
# << C17
