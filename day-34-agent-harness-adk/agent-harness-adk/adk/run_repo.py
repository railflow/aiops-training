"""One Kubernetes Job = one repository, ADK edition. Same worker contract as hand_rolled/agent_loop.py: env in, `RESULT {json}` out, same exit codes."""
import asyncio
import json
import os
import signal
import sys
import time
import warnings
from pathlib import Path

from google.adk import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types

from adk import tools as tl
from adk.models import MalformedOutput, ModelUnavailable
from adk.pipeline import build_app
from common import faults as F
from common import repos
from common.settings import Settings

warnings.filterwarnings("ignore")
USER = "harness"


# >> C16 structured logging and tracing
def log(cfg: Settings, event: str, **kv):
    print(json.dumps({"ts": round(time.time(), 3), "run": cfg.run_id, "repo": cfg.repo, "attempt": cfg.attempt, "event": event, **kv}), file=sys.stderr, flush=True)
# << C16


def result_of(cfg: Settings, state: dict, status: str | None, resumed: bool) -> dict:
    cov = state.get("coverage", [])
    status = status or state.get("status") or ("succeeded" if state.get("pr_url") else "below_target")
    return {"repo": cfg.repo, "status": status, "coverage_before": cov[0] if cov else None, "coverage_after": cov[-1] if cov else None, "steps": state.get("steps", 0),
            "cost_usd": round(state.get("spent", 0.0), 4), "pr": state.get("pr_url"), "resumed": resumed, "attempt": cfg.attempt}


async def run(cfg: Settings, faults: list[str], repo_dir: str) -> tuple[dict, int]:
    app = build_app(cfg, faults)
    # >> C12 checkpoint, resume and session persistence
    Path(cfg.state_dir).mkdir(parents=True, exist_ok=True)
    sessions = SqliteSessionService(str(Path(cfg.state_dir) / f"{cfg.repo}.db"))
    runner = Runner(app=app, session_service=sessions)
    session = await sessions.get_session(app_name=app.name, user_id=USER, session_id=cfg.repo)
    resumed = bool(session and session.events)
    if not session:
        session = await sessions.create_session(app_name=app.name, user_id=USER, session_id=cfg.repo, state={
            "repo": cfg.repo, "repo_dir": repo_dir, "target": cfg.target, "budget_usd": cfg.budget_usd, "approval": cfg.approval,
            "approval_wait_s": cfg.approval_wait_s, "state_dir": cfg.state_dir, "step_timeout_s": cfg.step_timeout_s, "faults": faults})
    kwargs = ({"invocation_id": session.events[-1].invocation_id} if resumed else
              {"new_message": types.Content(role="user", parts=[types.Part(text=f"Raise test coverage of repo={cfg.repo} to {cfg.target}%. Use the tools; stop when done or stuck.")])})
    # << C12
    # >> C18 graceful cancellation
    abort = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, abort.set)
    # << C18
    # >> C10 timeouts per step and per job
    asyncio.get_running_loop().call_later(cfg.job_deadline_s, lambda: (abort.set(), deadline.append(True)))
    deadline: list[bool] = []
    # << C10
    status, code = None, 0
    try:
        # >> C06 loop termination
        async for event in runner.run_async(user_id=USER, session_id=cfg.repo, run_config=RunConfig(max_llm_calls=cfg.max_steps), abort_signal=abort, **kwargs):
            log(cfg, "event", author=event.author, final=event.is_final_response())
        # << C06
    except Exception as e:  # noqa: BLE001
        name = type(e).__name__
        if name == "LlmCallsLimitExceededError":
            status = "max_steps"
        elif isinstance(e, MalformedOutput):
            status = "malformed_output"
        elif isinstance(e, ModelUnavailable):
            state = (await sessions.get_session(app_name=app.name, user_id=USER, session_id=cfg.repo)).state
            return {"repo": cfg.repo, "status": "retryable", "error": str(e), "attempt": cfg.attempt}, 75
        else:
            raise
    state = (await sessions.get_session(app_name=app.name, user_id=USER, session_id=cfg.repo)).state
    if abort.is_set():
        status, code = ("deadline", 0) if deadline else ("cancelled", 143)
    return result_of(cfg, dict(state), status, resumed), code


def main() -> int:
    cfg = Settings.from_env()
    faults = F.parse(cfg.chaos, cfg.repo)
    F.die_if_planned(faults, cfg.attempt)
    repo_dir = os.environ.get("REPO_DIR") or repos.materialise({"name": cfg.repo, "domain": cfg.domain, "seed": cfg.seed}, cfg.work_dir)
    tl.HANG_FAULTS.clear()
    result, code = asyncio.run(run(cfg, faults, repo_dir))
    print("RESULT " + json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
