"""The model client of the hand-rolled harness: a mock for the lab, an OpenAI-compatible HTTP client for the real thing."""
import json
import os
import random
import time
import urllib.error
import urllib.request

from common.faults import RateLimited, RateLimiter
from common.mock_llm import Call, Reply, decide, estimate_tokens


# >> LAB the mock model client
class MockLLM:
    def __init__(self, role: str, target: float, faults: frozenset, limiter: RateLimiter):
        self.role, self.target, self.faults, self.limiter = role, target, faults, limiter

    def complete(self, history: list[dict], tools: list[dict]) -> Reply:
        self.limiter.check()
        return decide(self.role, history, self.target, self.faults)
# << LAB


class HttpLLM:
    """POST {LLM_BASE_URL}/chat/completions with tools. Needs LLM_BASE_URL and LLM_API_KEY. Only shape-tested; never run against a real service here."""

    def __init__(self, model: str):
        self.url, self.key, self.model = os.environ["LLM_BASE_URL"].rstrip("/"), os.environ["LLM_API_KEY"], model

    def complete(self, history: list[dict], tools: list[dict]) -> Reply:
        messages = []
        for i, m in enumerate(history):
            if m["role"] == "tool":
                messages.append({"role": "tool", "tool_call_id": f"call-{i}", "content": json.dumps(m["result"])})
            elif m["role"] == "assistant" and m.get("calls"):
                c = m["calls"][0]
                messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": f"call-{i + 1}", "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}]})
            else:
                messages.append({"role": m["role"], "content": m.get("text") or ""})
        body = json.dumps({"model": self.model, "messages": messages, "tools": [{"type": "function", "function": t} for t in tools]}).encode()
        req = urllib.request.Request(f"{self.url}/chat/completions", body, {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimited(float(e.headers.get("Retry-After", 0) or 0))
            raise
        msg = data["choices"][0]["message"]
        usage = data.get("usage", {})
        reply = Reply(text=msg.get("content"), prompt_tokens=usage.get("prompt_tokens", 0), completion_tokens=usage.get("completion_tokens", 0))
        for tc in msg.get("tool_calls") or []:
            try:
                reply.calls.append(Call(tc["function"]["name"], json.loads(tc["function"]["arguments"]), tc.get("id", "")))
            except ValueError:
                reply.error = "tool call arguments are not valid JSON"
        return reply


# >> C01 concurrency, rate limits and backoff
def call_with_backoff(llm, history, tools, attempts: int = 6, sleep=time.sleep):
    """Retry 429s and transient network errors with exponential backoff and jitter, honouring Retry-After."""
    for n in range(attempts):
        try:
            return llm.complete(history, tools)
        except RateLimited as e:
            wait = max(e.retry_after, min(30.0, 0.5 * 2 ** n) * random.uniform(0.5, 1.0))
        except (urllib.error.URLError, TimeoutError):
            wait = min(30.0, 0.5 * 2 ** n) * random.uniform(0.5, 1.0)
        if n == attempts - 1:
            raise TransientLLMError(f"model unavailable after {attempts} attempts")
        sleep(wait)
# << C01


class TransientLLMError(Exception):
    """Retry later: the orchestrator treats exit code 75 as retryable."""
