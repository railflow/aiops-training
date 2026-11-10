#!/usr/bin/env python3
"""Ask one or more models the same question through an OpenAI-compatible gateway and compare answer, latency and cost.
  export OPENROUTER_API_KEY=...        (from OpenBao; see the page)
  python3 gateway/ask.py "Explain a Kubernetes Job in one sentence." --model <slug-a> --model <slug-b>
  python3 gateway/ask.py "..." --model <slug> --base-url http://127.0.0.1:8099/v1      # point at any compatible server
Model slugs: list them from the gateway (GET /models); do not copy ids from old blog posts."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import llm  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--base-url")
    ap.add_argument("--max-tokens", type=int, default=256)
    a = ap.parse_args(argv)
    rc = 0
    for m in a.model:
        try:
            r = llm.chat(m, [{"role": "user", "content": a.prompt}], max_tokens=a.max_tokens, base_url=a.base_url)
        except llm.LLMError as e:
            print(f"[{m}] ERROR: {e}", file=sys.stderr)
            rc = 1
            continue
        u = r["usage"]
        print(f"[{m}] {r['latency_s']:.2f}s  in={u.get('prompt_tokens')} out={u.get('completion_tokens')} cost={u.get('cost', 'n/a')}")
        print(r["text"].strip(), "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
