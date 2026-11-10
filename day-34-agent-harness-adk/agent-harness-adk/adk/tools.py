"""Tools as plain Python functions. ADK reads the signature and docstring and builds the schema the model sees.

The shared logic lives in common/repo_tools.py (identical for both engines). These wrappers only add session state.
State holds repo_dir, coverage history, spent dollars, steps and the PR url; it is saved with every event.
"""
import asyncio
import json

from google.adk.tools import ToolContext

from common import faults as F
from common import repo_tools as T

MAX_RESULT_CHARS = 8000
HANG_FAULTS: dict[str, list[str]] = {}


def _cap(out: dict) -> dict:
    text = json.dumps(out)
    return out if len(text) <= MAX_RESULT_CHARS else {"truncated": True, "text": text[:MAX_RESULT_CHARS]}


async def run_tests(tool_context: ToolContext) -> dict:
    """Run the test suite with coverage. Returns the coverage percentage, failing tests and the least-covered functions."""
    st = tool_context.state
    timeout = st.get("step_timeout_s", 120.0)
    # >> C10 timeouts per step and per job
    try:
        out = await asyncio.wait_for(asyncio.to_thread(lambda: (F.die_at_test(st.get("faults", []), st["state_dir"], st["repo"]), F.hang_if_planned(HANG_FAULTS.setdefault(st["repo"], list(st.get("faults", [])))), T.run_tests(st["repo_dir"]))[2]), timeout)
    except asyncio.TimeoutError:
        return {"error": f"run_tests timed out after {timeout}s"}
    # << C10
    st["coverage"] = [*st.get("coverage", []), out["coverage"]]
    return _cap(out)


def read_file(path: str, tool_context: ToolContext) -> dict:
    """Read a file from the repository."""
    return _cap(T.read_file(tool_context.state["repo_dir"], path))


def write_test_file(path: str, content: str, covers: list[str], tool_context: ToolContext) -> dict:
    """Create or replace tests/test_<name>.py. `covers` lists the function names the file targets."""
    return T.write_test_file(tool_context.state["repo_dir"], path, content, covers)


def git_commit(branch: str, message: str, tool_context: ToolContext) -> dict:
    """Commit the new tests on a branch named agent/<name>."""
    return T.git_commit(tool_context.state["repo_dir"], branch, message)


def open_pr(branch: str, title: str, body: str, tool_context: ToolContext) -> dict:
    """Open a pull request for the branch."""
    out = T.open_pr(tool_context.state["repo_dir"], branch, title, body)
    if "url" in out:
        tool_context.state["pr_url"] = out["url"]
    return out
