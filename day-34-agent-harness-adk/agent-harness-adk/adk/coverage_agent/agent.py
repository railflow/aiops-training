"""Entry point for `adk run adk/coverage_agent` and `adk web adk`: the same pipeline, with state seeded from the environment.

Set REPO_DIR to a repository (python3 -m common.repos can stamp one) and LLM_MODE=gemini plus GOOGLE_API_KEY for a real model.
Not exercised in this lab: the interactive CLI and web UI.
"""
import os

from adk.pipeline import build_app
from common.settings import Settings

cfg = Settings(repo=os.environ.get("REPO_NAME", "demo"), llm=os.environ.get("LLM_MODE", "mock"), model=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
               state_dir=os.environ.get("STATE_DIR", "/tmp/state"))


def _seed(callback_context):
    s = callback_context.state
    for k, v in {"repo": cfg.repo, "repo_dir": os.environ.get("REPO_DIR", "."), "target": cfg.target, "budget_usd": cfg.budget_usd, "approval": "deny",
                 "approval_wait_s": 0.0, "state_dir": cfg.state_dir, "step_timeout_s": cfg.step_timeout_s, "faults": []}.items():
        s.setdefault(k, v)


root_agent = build_app(cfg, []).root_agent
root_agent.before_agent_callback = _seed
