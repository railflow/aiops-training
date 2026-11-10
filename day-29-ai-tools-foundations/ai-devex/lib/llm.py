"""One tiny OpenAI-compatible chat client (stdlib only) so every lab talks to a gateway the same way.

Env: LLM_BASE_URL (default OpenRouter's), OPENROUTER_API_KEY (or LLM_API_KEY). The key is read from the environment only: never put it in a file in git.
Model names are always passed in by the caller; this module has no model ids in it on purpose (they change)."""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://openrouter.ai/api/v1"


class LLMError(Exception):
    pass


def api_key():
    k = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY")
    if not k:
        raise LLMError("no API key: export OPENROUTER_API_KEY (from OpenBao or your password manager; never type it into a file in git)")
    return k


def chat(model, messages, *, max_tokens=512, temperature=0, base_url=None, timeout=60, extra=None):
    """Returns {"text", "usage", "latency_s", "model"}. `extra` is merged into the JSON body (e.g. {"reasoning": ...}); check your gateway's docs."""
    base = (base_url or os.environ.get("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    body.update(extra or {})
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + api_key(), "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code} from {base}: {e.read()[:300].decode(errors='replace')}") from None
    except urllib.error.URLError as e:
        raise LLMError(f"cannot reach {base}: {e.reason}") from None
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise LLMError(f"unexpected response shape: {str(data)[:300]}") from None
    return {"text": text, "usage": data.get("usage", {}), "latency_s": time.time() - t0, "model": data.get("model", model)}
