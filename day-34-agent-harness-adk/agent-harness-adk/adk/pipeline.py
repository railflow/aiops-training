"""The same coverage agent, written with Google ADK.

analyzer -> loop(improver, gate) -> publisher. ADK runs the model/tool loop, passes context between agents, persists the session and lets us resume.
What is left is the part that is specific to this job: when to stop, what a budget is, who approves a PR.
"""
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events import Event, EventActions
from google.adk.models import LlmResponse
from google.adk.plugins.context_filter_plugin import ContextFilterPlugin
from google.genai import types

from adk import tools as tl
from adk.models import build_model
from common import faults as F
from common.approval import approval
from common.mock_llm import PRICE_PER_1K_TOKENS
from common.settings import Settings

ANALYZER = "Measure the baseline: run the tests once and report the coverage. Do nothing else."
IMPROVER = ("Raise coverage. Read the least-covered functions from the latest test run, write tests for several of them with write_test_file, run the tests, fix or drop any generated test that fails. "
            "When one round is verified, reply with a one-line summary.")
PUBLISHER = "Commit the new tests on a branch agent/coverage-<repo> with git_commit, then open a pull request with open_pr, then reply 'pull request opened'."


# >> C07 tool dispatch, tool errors, malformed output
def tool_errors(tool, args, tool_context, error):
    """A tool bug or bad arguments become a message the model can read, not a crash."""
    return {"error": f"{type(error).__name__}: {error}"}
# << C07


# >> C09 token and cost budgets
def count_cost(callback_context: CallbackContext, llm_response: LlmResponse):
    u = llm_response.usage_metadata
    tokens = ((u.prompt_token_count or 0) + (u.candidates_token_count or 0)) if u else 0
    s = callback_context.state
    s["spent"] = round(s.get("spent", 0.0) + tokens / 1000 * PRICE_PER_1K_TOKENS, 6)
    s["steps"] = s.get("steps", 0) + 1


def budget_guard(callback_context: CallbackContext, llm_request):
    s = callback_context.state
    if s.get("spent", 0.0) >= s["budget_usd"]:
        s["status"] = "budget_exhausted"
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="budget exhausted; stopping")]))
    return None
# << C09


# >> C08 context growth and compaction
def keep_newest_test_run(contents: list[types.Content]) -> list[types.Content]:
    """Old test reports are the bulk of the context. Keep every call, blank all but the newest run_tests result."""
    idx = [i for i, c in enumerate(contents) for p in c.parts or [] if p.function_response and p.function_response.name == "run_tests"]
    out = []
    for i, c in enumerate(contents):
        if i in idx[:-1]:
            parts = [types.Part(function_response=types.FunctionResponse(id=p.function_response.id, name="run_tests", response={"elided": True})) for p in c.parts]
            c = types.Content(role=c.role, parts=parts)
        out.append(c)
    return out
# << C08


# >> C06 loop termination
class CoverageGate(BaseAgent):
    """LoopAgent only stops at max_iterations or when an event escalates. This agent is where 'done' and 'stuck' are decided."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        s = ctx.session.state
        cov = s.get("coverage", [])
        history = [*s.get("round_coverage", []), cov[-1] if cov else 0.0]
        status = s.get("status")
        if status is None and cov and cov[-1] >= s["target"]:
            status = "succeeded"
        elif status is None and len(history) >= 3 and history[-1] <= history[-2] <= history[-3]:
            status = "no_progress"
        yield Event(author=self.name, actions=EventActions(escalate=status is not None, state_delta={"round_coverage": history, **({"status": status} if status else {})}))
# << C06


# >> C17 human approval
def approval_gate(tool, args, tool_context):
    if tool.name != "open_pr":
        return None
    verdict = approval(tool_context.state["approval"], tool_context.state["repo"], tool_context.state["approval_wait_s"])
    if verdict == "approved":
        return None
    tool_context.state["status"] = "awaiting_approval" if verdict == "pending" else "approval_denied"
    tool_context.actions.skip_summarization = True  # end the turn: do not hand a refusal back to the model to argue with
    return {"error": f"approval {verdict}", "approval": verdict}


def skip_if_not_ready(callback_context: CallbackContext):
    if callback_context.state.get("status") != "succeeded":
        return types.Content(role="model", parts=[types.Part(text="skipped: nothing worth publishing")])
    return None
# << C17


def build_app(cfg: Settings, faults: list[str]) -> App:
    def llm(role):
        return build_model(role, cfg.target, faults, cfg.repo, mode=cfg.llm, name=cfg.model)

    common = dict(before_model_callback=budget_guard, after_model_callback=count_cost, on_tool_error_callback=tool_errors)
    analyzer = LlmAgent(name="analyzer", model=llm("analyze"), instruction=ANALYZER, tools=[tl.run_tests], output_key="baseline", **common)
    improver = LlmAgent(name="improver", model=llm("improve"), instruction=IMPROVER, tools=[tl.run_tests, tl.read_file, tl.write_test_file], **common)
    improve_loop = LoopAgent(name="improve_loop", sub_agents=[improver, CoverageGate(name="gate")], max_iterations=8)
    publisher = LlmAgent(name="publisher", model=llm("publish"), instruction=PUBLISHER, tools=[tl.git_commit, tl.open_pr], before_tool_callback=approval_gate,
                         before_agent_callback=skip_if_not_ready, **common)
    root = SequentialAgent(name="coverage_pipeline", sub_agents=[analyzer, improve_loop, publisher])
    # >> C12 checkpoint, resume and session persistence
    resumability = ResumabilityConfig(is_resumable=True)
    # << C12
    return App(name="coverage", root_agent=root, resumability_config=resumability,
               plugins=[ContextFilterPlugin(custom_filter=keep_newest_test_run)])
