"""Worker settings, read from the environment the Job sets. Shared by both engines."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    repo: str
    domain: str = "billing"
    seed: int = 1000
    target: float = 80.0
    max_steps: int = 30
    budget_usd: float = 0.25
    step_timeout_s: float = 120.0
    job_deadline_s: float = 900.0
    context_tokens: int = 6000
    state_dir: str = "/tmp/state"
    work_dir: str = "/work"
    approval: str = "auto"
    approval_wait_s: float = 0.0
    attempt: int = 1
    run_id: str = "local"
    chaos: str = ""
    llm: str = "mock"
    model: str = "any-model"

    @classmethod
    def from_env(cls, env=os.environ):
        g = lambda k, d: type(d)(env.get(k, d))  # noqa: E731
        return cls(repo=env["REPO_NAME"], domain=g("REPO_DOMAIN", "billing"), seed=g("REPO_SEED", 1000), target=g("TARGET_COVERAGE", 80.0),
                   max_steps=g("MAX_STEPS", 30), budget_usd=g("BUDGET_USD", 0.25), step_timeout_s=g("STEP_TIMEOUT_S", 120.0), job_deadline_s=g("JOB_DEADLINE_S", 900.0),
                   context_tokens=g("CONTEXT_TOKENS", 6000), state_dir=g("STATE_DIR", "/tmp/state"), work_dir=g("WORK_DIR", "/work"), approval=g("APPROVAL", "auto"),
                   approval_wait_s=g("APPROVAL_WAIT_S", 0.0), attempt=g("ATTEMPT", 1), run_id=g("RUN_ID", "local"), chaos=g("CHAOS", ""), llm=g("LLM_MODE", "mock"), model=g("LLM_MODEL", "any-model"))
