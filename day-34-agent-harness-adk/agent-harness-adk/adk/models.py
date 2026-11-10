"""Models for the ADK agents: an offline stub for the lab, Gemini or LiteLLM for the real thing.

ADK does not retry a failing model call for you inside an agent tree (see docs), so one thin wrapper owns that.
"""
import asyncio
import os
import random

from google.adk.models import BaseLlm, LlmResponse
from google.genai import types

from common import faults as F
from common.mock_llm import decide


class ModelUnavailable(Exception):
    """Retry later: run_repo turns it into exit code 75."""


class MalformedOutput(Exception):
    pass


# >> LAB the stub model
def to_history(contents: list[types.Content]) -> list[dict]:
    """ADK conversation -> the plain history the mock policy reads. Only the stub needs this."""
    out = []
    for c in contents:
        for p in c.parts or []:
            if p.function_call:
                out.append({"role": "assistant", "text": None, "calls": [{"name": p.function_call.name, "args": dict(p.function_call.args or {})}]})
            elif p.function_response:
                out.append({"role": "tool", "name": p.function_response.name, "result": dict(p.function_response.response or {})})
            elif p.text:
                out.append({"role": "assistant" if c.role == "model" else "user", "text": p.text, "calls": []})
    return out


_limiters: dict[str, F.RateLimiter] = {}


class StubModel(BaseLlm):
    """The mock policy behind ADK's model interface. It is not a model."""

    model: str = "stub"
    role: str = "all"
    target: float = 80.0
    faults: list[str] = []
    repo: str = ""

    async def generate_content_async(self, llm_request, stream: bool = False):
        limiter = _limiters.setdefault(self.repo, F.RateLimiter(self.faults))
        limiter.check()
        reply = decide(self.role, to_history(llm_request.contents), self.target, F.model_faults(self.faults))
        usage = types.GenerateContentResponseUsageMetadata(prompt_token_count=reply.prompt_tokens, candidates_token_count=reply.completion_tokens)
        if reply.error:
            yield LlmResponse(error_code="MALFORMED_FUNCTION_CALL", error_message=reply.error, usage_metadata=usage)
            return
        parts = [types.Part(function_call=types.FunctionCall(name=c.name, args=c.args)) for c in reply.calls] or [types.Part(text=reply.text or "")]
        yield LlmResponse(content=types.Content(role="model", parts=parts), usage_metadata=usage)
# << LAB


# >> C01 concurrency, rate limits and backoff
# >> C07 tool dispatch, tool errors, malformed output
class Resilient(BaseLlm):
    """Wraps any model: backs off on 429s and asks again when the reply is malformed. Gemini can also retry by itself (retry_options)."""

    model: str = "resilient"
    inner: BaseLlm
    attempts: int = 6
    strikes: int = 3

    async def generate_content_async(self, llm_request, stream: bool = False):
        bad = 0
        for n in range(self.attempts + self.strikes):
            try:
                responses = [r async for r in self.inner.generate_content_async(llm_request, stream=stream)]
            except F.RateLimited as e:
                if n >= self.attempts - 1:
                    raise ModelUnavailable(f"model unavailable after {self.attempts} attempts") from e
                await asyncio.sleep(max(e.retry_after, min(30.0, 0.5 * 2 ** n) * random.uniform(0.5, 1.0)))
                continue
            if responses and responses[-1].error_code:
                bad += 1
                if bad >= self.strikes:
                    raise MalformedOutput(responses[-1].error_message)
                llm_request.contents.append(types.Content(role="user", parts=[types.Part(text=f"Your last reply was rejected: {responses[-1].error_message}. Reply again with a valid tool call.")]))
                continue
            for r in responses:
                yield r
            return
# << C07
# << C01


def build_model(role: str, target: float, faults: list[str], repo: str, mode: str = "mock", name: str = "gemini-2.5-flash") -> BaseLlm:
    if mode == "mock":
        return Resilient(inner=StubModel(role=role, target=target, faults=faults, repo=repo))
    if name.startswith("gemini"):
        from google.adk.models.google_llm import Gemini

        return Gemini(model=name, retry_options=types.HttpRetryOptions(attempts=5, initial_delay=1.0, max_delay=30.0))
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(model=name, api_base=os.environ.get("LLM_BASE_URL"))
