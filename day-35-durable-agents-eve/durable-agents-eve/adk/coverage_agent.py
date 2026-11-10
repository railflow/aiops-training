"""The coverage agent as a Google ADK app (google-adk 2.13.0): same scenario, same scripted model, same tools as the Eve lab.

Durability in ADK is two pieces you assemble: a persistent session service (here SQLite) and, for crash recovery, the
experimental ResumabilityConfig. The approval gate is `FunctionTool(..., require_confirmation=True)`.
"""
import os
import warnings

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.apps.app import ResumabilityConfig
from google.adk.models import BaseLlm, LlmResponse
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.tools import FunctionTool
from google.genai import types

import lab_common as lab

warnings.filterwarnings("ignore")
APP_NAME, USER = "coverage", "lab"


def run_tests(repo: str) -> dict:
    """Run the repository's tests and report line coverage."""
    return lab.run_tests(repo)


def write_test_file(repo: str) -> dict:
    """Write one generated test file for the least-covered code."""
    return lab.write_test_file(repo)


def git_commit(repo: str) -> dict:
    """Commit the generated tests on a branch."""
    return lab.git_commit(repo)


def open_pr(repo: str) -> dict:
    """Open a pull request for the committed tests. A person must approve each call."""
    return lab.open_pr(repo)


def results_of(contents: list[types.Content]) -> tuple[str, list[tuple[str, bool]], str | None]:
    """ADK conversation -> (task text, [(tool, interrupted)], stop reason)."""
    task, results, stop = "", [], None
    for c in contents:
        for p in c.parts or []:
            if p.text and c.role == "user" and not task:
                task = p.text
            elif p.function_response:
                body = str(p.function_response.response)
                if p.function_response.name == "adk_request_confirmation":
                    continue
                if "requires confirmation" in body:
                    continue  # the gate answered instead of the tool: the step is not done
                if "rejected" in body:
                    stop = "stopped: pull request not approved"
                    continue
                results.append((p.function_response.name, False))
    return task, results, stop


class ScriptedModel(BaseLlm):
    """The scripted policy behind ADK's model interface. It is not a model."""

    model: str = "scripted"

    async def generate_content_async(self, llm_request, stream: bool = False):
        task, results, stop = results_of(llm_request.contents)
        d = {"text": stop} if stop else lab.decide(task, results)
        part = types.Part(text=d["text"]) if "text" in d else types.Part(function_call=types.FunctionCall(name=d["tool"], args=d["args"]))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def build_app() -> App:
    tools = [FunctionTool(run_tests), FunctionTool(write_test_file), FunctionTool(git_commit), FunctionTool(open_pr, require_confirmation=True)]
    agent = LlmAgent(name="coverage_agent", model=ScriptedModel(), instruction="Raise test coverage, then open one pull request.", tools=tools)
    return App(name=APP_NAME, root_agent=agent, resumability_config=ResumabilityConfig(is_resumable=True))


def build_runner() -> tuple[Runner, SqliteSessionService]:
    sessions = SqliteSessionService(os.path.join(str(lab.lab_dir()), "adk-sessions.db"))
    return Runner(app=build_app(), session_service=sessions), sessions
