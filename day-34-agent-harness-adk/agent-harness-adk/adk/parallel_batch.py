"""ParallelAgent: in-process concurrency for a handful of independent sub-tasks inside ONE Job.

It is not how you run 100 repositories: every branch shares one session (state keys must be unique per branch)
and one process, one pod, one memory limit. 100 repositories are 100 Jobs (fanout/orchestrator.py).
Here: measure the coverage of a few repositories at once, then merge the answers.
"""
import asyncio
import re
import sys

from google.adk import Runner
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.models import BaseLlm, LlmResponse
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

from common import repo_tools as T
from common import repos

DIRS: dict[str, str] = {}


def measure_coverage(repo: str, tool_context: ToolContext) -> dict:
    """Run a repository's tests and return its coverage percentage."""
    out = T.run_tests(DIRS[repo])
    return {"repo": repo, "coverage": out["coverage"], "uncovered": out["uncovered_total"]}


class ScanStub(BaseLlm):
    """Offline stand-in: call the tool for the repo named in the instruction, then say the number."""

    model: str = "scan-stub"

    async def generate_content_async(self, llm_request, stream: bool = False):
        repo = str(llm_request.config.system_instruction).split("repo=")[1].split()[0]
        last = llm_request.contents[-1].parts[0]
        if last.function_response is None:
            part = types.Part(function_call=types.FunctionCall(name="measure_coverage", args={"repo": repo}))
        else:
            part = types.Part(text=f"{repo}: {last.function_response.response['coverage']}% covered")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def build(repo_names: list[str], model: BaseLlm | None = None) -> SequentialAgent:
    model = model or ScanStub()
    scanners = [LlmAgent(name=f"scan_{i}", model=model, instruction=f"Measure coverage for repo={name} with measure_coverage and report it.", tools=[measure_coverage], output_key=f"report_{i}")
                for i, name in enumerate(repo_names)]
    merge = LlmAgent(name="merge", model=_Merge(), instruction="Merge the reports.", output_key="merged")
    return SequentialAgent(name="batch", sub_agents=[ParallelAgent(name="scan_all", sub_agents=scanners), merge])


class _Merge(BaseLlm):
    model: str = "merge-stub"

    async def generate_content_async(self, llm_request, stream: bool = False):
        found = sorted({m for c in llm_request.contents for p in c.parts or [] if p.text for m in re.findall(r"[\w.-]+: [\d.]+% covered", p.text)})
        text = " | ".join(found)
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text or "no reports")]))


async def run(repo_names: list[str], workdir: str) -> dict:
    for spec in repos.make_specs(len(repo_names)):
        DIRS[spec["name"]] = repos.materialise(spec, workdir)
    svc = InMemorySessionService()
    runner = Runner(app_name="batch", agent=build(list(DIRS)), session_service=svc)
    await svc.create_session(app_name="batch", user_id="u", session_id="s")
    authors = []
    async for ev in runner.run_async(user_id="u", session_id="s", new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        authors.append(ev.author)
    state = (await svc.get_session(app_name="batch", user_id="u", session_id="s")).state
    return {"authors": authors, "reports": [state[k] for k in sorted(state) if k.startswith("report_")], "merged": state.get("merged")}


if __name__ == "__main__":
    import tempfile

    print(asyncio.run(run(["x"] * int(sys.argv[1] if len(sys.argv) > 1 else 3), tempfile.mkdtemp())))
