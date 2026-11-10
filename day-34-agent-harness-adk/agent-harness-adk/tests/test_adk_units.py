"""ADK behaviours the Day 34 page states, checked in isolation against the pinned version."""
import asyncio
import warnings

import pytest
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.models import BaseLlm, LlmResponse
from google.adk.plugins import ReflectAndRetryToolPlugin
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

from adk import pipeline
from adk import tools as tl
from common import repo_tools as T

warnings.filterwarnings("ignore")


class CallOnce(BaseLlm):
    """Calls the named tool with the given args up to `times` times, then says 'ok'."""

    model: str = "call-once"
    tool: str
    args: dict = {}
    times: int = 1

    async def generate_content_async(self, llm_request, stream=False):
        seen = sum(1 for c in llm_request.contents for p in c.parts or [] if p.function_response)
        part = types.Part(function_call=types.FunctionCall(name=self.tool, args=self.args)) if seen < self.times else types.Part(text="ok")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def converse(agent, plugins=(), state=None):
    async def go():
        app = App(name="u", root_agent=agent, plugins=list(plugins))
        svc = InMemorySessionService()
        runner = Runner(app=app, session_service=svc)
        await svc.create_session(app_name="u", user_id="u", session_id="s", state=state or {})
        out = []
        async for ev in runner.run_async(user_id="u", session_id="s", new_message=types.Content(role="user", parts=[types.Part(text="go")])):
            out += [p.function_response.response for p in (ev.content.parts if ev.content else []) if p.function_response]
        return out

    return asyncio.run(go())


def boom() -> dict:
    """Always fails."""
    raise ValueError("nope")


def typed(x: int, tool_context: ToolContext) -> dict:
    """Takes an int."""
    return {"type": type(x).__name__}


def test_an_unhandled_tool_exception_ends_the_run():
    agent = LlmAgent(name="a", model=CallOnce(tool="boom"), instruction="x", tools=[boom])
    with pytest.raises(ValueError, match="nope"):
        converse(agent)


def test_our_error_callback_turns_a_tool_exception_into_a_message(repo_dir):
    agent = LlmAgent(name="a", model=CallOnce(tool="write_test_file", args={"path": "src/evil.py", "content": "x", "covers": []}), instruction="x",
                     tools=[tl.write_test_file], on_tool_error_callback=pipeline.tool_errors)
    out = converse(agent, state={"repo_dir": repo_dir})
    assert "tests/test_" in out[0]["error"]


def test_reflect_and_retry_plugin_gives_the_model_a_budget_then_raises_again():
    agent = LlmAgent(name="a", model=CallOnce(tool="boom", times=5), instruction="x", tools=[boom])
    with pytest.raises(RuntimeError, match="reflect_retry_tool_plugin"):
        converse(agent, plugins=[ReflectAndRetryToolPlugin(max_retries=2)])


def test_tool_arguments_are_not_type_checked():
    agent = LlmAgent(name="a", model=CallOnce(tool="typed", args={"x": "not an int"}), instruction="x", tools=[typed])
    assert converse(agent)[0] == {"type": "str"}


def test_an_unknown_tool_name_is_reported_to_the_model_not_raised():
    agent = LlmAgent(name="a", model=CallOnce(tool="no_such_tool"), instruction="x", tools=[boom])
    assert "no_such_tool" in str(converse(agent)[0])


def test_a_model_error_propagates_and_the_agent_does_not_retry_it():
    from common.faults import RateLimited

    class Flaky(BaseLlm):
        model: str = "flaky"

        async def generate_content_async(self, llm_request, stream=False):
            raise RateLimited(0)
            yield  # pragma: no cover

    with pytest.raises(RateLimited):
        converse(LlmAgent(name="a", model=Flaky(), instruction="x"))


def test_templated_agents_warn_that_they_are_deprecated():
    from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

    a = LlmAgent(name="a", model=CallOnce(tool="boom"), instruction="x")
    for ctor, kw in [(SequentialAgent, {}), (LoopAgent, {"max_iterations": 1}), (ParallelAgent, {})]:
        with pytest.warns(DeprecationWarning, match="deprecated in favor of Workflow"):
            ctor(name=ctor.__name__.lower(), sub_agents=[LlmAgent(name=f"x{ctor.__name__}", model=CallOnce(tool="boom"), instruction="x")], **kw)
    assert a


def test_pinned_version():
    import importlib.metadata as md

    assert md.version("google-adk") == "2.13.0"


class FailsThenWorks(BaseLlm):
    model: str = "fails-then-works"
    failures: int = 1

    async def generate_content_async(self, llm_request, stream=False):
        seen = _calls.setdefault(id(self), 0)
        _calls[id(self)] = seen + 1
        if seen < self.failures:
            raise ConnectionError("503")
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="ok")]))


_calls: dict = {}


def test_retry_config_on_an_llm_agent_in_a_sequence_does_not_retry_a_model_error():
    from google.adk.agents import SequentialAgent
    from google.adk.workflow._retry_config import RetryConfig

    model = FailsThenWorks()
    agent = LlmAgent(name="a", model=model, instruction="x", retry_config=RetryConfig(max_attempts=3))
    with pytest.raises(ConnectionError):
        converse(SequentialAgent(name="s", sub_agents=[agent]))
    assert _calls[id(model)] == 1


def test_an_error_callback_that_returns_nothing_does_not_retry():
    fired = []
    model = FailsThenWorks()
    agent = LlmAgent(name="a", model=model, instruction="x", on_model_error_callback=lambda ctx, req, err: fired.append(err) or None)
    with pytest.raises(ConnectionError):
        converse(agent)
    assert len(fired) == 1 and _calls[id(model)] == 1


def test_missing_mandatory_arguments_are_reported_to_the_model():
    agent = LlmAgent(name="a", model=CallOnce(tool="typed", args={}), instruction="x", tools=[typed])
    assert "mandatory" in str(converse(agent)[0])


def test_a_malformed_model_reply_is_passed_through_as_an_error_response_without_a_retry():
    class Malformed(BaseLlm):
        model: str = "malformed"

        async def generate_content_async(self, llm_request, stream=False):
            yield LlmResponse(error_code="MALFORMED_FUNCTION_CALL", error_message="bad")

    async def go():
        app = App(name="u", root_agent=LlmAgent(name="a", model=Malformed(), instruction="x"))
        svc = InMemorySessionService()
        runner = Runner(app=app, session_service=svc)
        await svc.create_session(app_name="u", user_id="u", session_id="s")
        return [ev async for ev in runner.run_async(user_id="u", session_id="s", new_message=types.Content(role="user", parts=[types.Part(text="go")]))]

    events = asyncio.run(go())
    assert len(events) == 1 and events[0].error_code == "MALFORMED_FUNCTION_CALL"


def test_build_model_picks_the_connector_and_never_sends_a_request(monkeypatch):
    from google.adk.models.google_llm import Gemini

    from adk.models import Resilient, build_model

    assert isinstance(build_model("improve", 80, [], "r", mode="mock"), Resilient)
    model = build_model("improve", 80, [], "r", mode="gemini", name="gemini-2.5-flash")
    assert isinstance(model, Gemini) and model.retry_options.attempts == 5
