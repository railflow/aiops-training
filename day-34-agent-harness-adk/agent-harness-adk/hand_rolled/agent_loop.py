"""The hand-rolled per-repo agent: one Kubernetes Job runs this for one repository.

It works. Read it as a catalogue: every `# >> Cnn` block is a case a real run forces you to handle.
Exit codes: 0 finished (see `status`), 75 retry later (model unavailable), 143 cancelled, 1 crash.
"""
import concurrent.futures as cf
import json
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from common import faults as F
from common import repo_tools as T
from common import repos
from common.approval import approval
from common.mock_llm import estimate_tokens
from common.settings import Settings
from hand_rolled.llm import HttpLLM, MockLLM, TransientLLMError, call_with_backoff

# >> C07 tool dispatch, tool errors, malformed output
TOOLS = [
    {"name": "run_tests", "description": "Run the tests with coverage; returns coverage, failures and the least-covered functions.", "parameters": {"type": "object", "properties": {}}},
    {"name": "read_file", "description": "Read a file from the repository.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_test_file", "description": "Create or replace tests/test_<name>.py.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "covers": {"type": "array", "items": {"type": "string"}}}, "required": ["path", "content", "covers"]}},
    {"name": "git_commit", "description": "Commit the new tests on a branch agent/<name>.", "parameters": {"type": "object", "properties": {"branch": {"type": "string"}, "message": {"type": "string"}}, "required": ["branch", "message"]}},
    {"name": "open_pr", "description": "Open a pull request for the branch.", "parameters": {"type": "object", "properties": {"branch": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}}, "required": ["branch", "title", "body"]}},
]
MAX_RESULT_CHARS = 8000
# << C07


@dataclass
class State:
    history: list = field(default_factory=list)
    step: int = 0
    spent: float = 0.0
    coverage: list = field(default_factory=list)
    recent_calls: list = field(default_factory=list)
    malformed: int = 0
    pr_url: str | None = None


# >> C16 structured logging and tracing
def log(cfg: Settings, event: str, **kv):
    print(json.dumps({"ts": round(time.time(), 3), "run": cfg.run_id, "repo": cfg.repo, "attempt": cfg.attempt, "event": event, **kv}), file=sys.stderr, flush=True)
# << C16


# >> C12 checkpoint, resume and session persistence
def state_path(cfg: Settings) -> Path:
    return Path(cfg.state_dir) / f"{cfg.repo}.json"


def save_state(cfg: Settings, st: State):
    p = state_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(st)))
    os.replace(tmp, p)  # atomic: a crash mid-write never leaves a half file


def load_state(cfg: Settings):
    p = state_path(cfg)
    return State(**json.loads(p.read_text())) if p.exists() else None
# << C12


# >> C08 context growth and compaction
def compact(history: list[dict], limit_tokens: int) -> list[dict]:
    """Keep the task and every call; replace the bodies of old tool results with a stub. Only the newest run_tests result is kept whole."""
    if estimate_tokens(history) <= limit_tokens:
        return history
    newest = max((i for i, m in enumerate(history) if m["role"] == "tool" and m["name"] == "run_tests"), default=-1)
    out = []
    for i, m in enumerate(history):
        if m["role"] == "tool" and i != newest and i != len(history) - 1:
            out.append({"role": "tool", "name": m["name"], "result": {"elided": True, **({"error": m["result"]["error"]} if "error" in m["result"] else {})}})
        else:
            out.append(m)
    return out
# << C08


# >> C10 timeouts per step and per job
def with_timeout(fn, seconds: float):
    """A hung tool must not hang the Job. Threads cannot be killed: the stuck call is abandoned and the process exits soon after."""
    ex = cf.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn)
    try:
        return fut.result(timeout=seconds)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
# << C10


def make_tools(repo_dir: str, faults: list, state_dir: str = "/tmp/state", repo: str = ""):
    return {
        "run_tests": lambda: (F.die_at_test(faults, state_dir, repo), F.hang_if_planned(faults), T.run_tests(repo_dir))[2],
        "read_file": lambda path: T.read_file(repo_dir, path),
        "write_test_file": lambda path, content, covers: T.write_test_file(repo_dir, path, content, covers),
        "git_commit": lambda branch, message: T.git_commit(repo_dir, branch, message),
        "open_pr": lambda branch, title, body: T.open_pr(repo_dir, branch, title, body),
    }


# >> C07 tool dispatch, tool errors, malformed output
def dispatch(cfg: Settings, tools: dict, call) -> dict:
    fn = tools.get(call.name)
    if fn is None:
        return {"error": f"unknown tool {call.name!r}; the tools are {sorted(tools)}"}
    # >> C17 human approval
    if call.name == "open_pr":
        verdict = approval(cfg.approval, cfg.repo, cfg.approval_wait_s)
        if verdict != "approved":
            return {"error": f"approval {verdict}", "approval": verdict}
    # << C17
    try:
        out = with_timeout(lambda: fn(**call.args), cfg.step_timeout_s)
    except T.ToolError as e:
        return {"error": str(e)}
    except TypeError as e:
        return {"error": f"bad arguments for {call.name}: {e}"}
    except cf.TimeoutError:
        return {"error": f"{call.name} timed out after {cfg.step_timeout_s}s"}
    except Exception as e:  # noqa: BLE001: a tool bug must not kill the loop; the model gets to see it
        return {"error": f"{type(e).__name__}: {e}"}
    text = json.dumps(out)
    return out if len(text) <= MAX_RESULT_CHARS else {"truncated": True, "text": text[:MAX_RESULT_CHARS]}
# << C07


def run(cfg: Settings, llm, tools: dict) -> dict:
    # >> C12 checkpoint, resume and session persistence
    st = load_state(cfg) or State(history=[{"role": "user", "text": f"Raise test coverage of repo={cfg.repo} to {cfg.target}%. Use the tools; stop when done or stuck."}])
    resumed = st.step > 0
    if st.history and st.history[-1]["role"] == "assistant" and st.history[-1].get("calls"):
        st.history.pop()  # the process died mid tool call; a call with no result would be rejected by a real API
    # << C12
    # >> C18 graceful cancellation
    cancelled = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: cancelled.update(flag=True))
    # << C18
    deadline = time.monotonic() + cfg.job_deadline_s
    status = None
    log(cfg, "start", resumed=resumed, step=st.step)
    while status is None:
        # >> C18 graceful cancellation
        if cancelled["flag"]:
            status = "cancelled"
        # << C18
        # >> C06 loop termination
        elif st.step >= cfg.max_steps:
            status = "max_steps"
        # << C06
        # >> C09 token and cost budgets
        elif st.spent >= cfg.budget_usd:
            status = "budget_exhausted"
        # << C09
        # >> C10 timeouts per step and per job
        elif time.monotonic() > deadline:
            status = "deadline"
        # << C10
        if status:
            break
        reply = call_with_backoff(llm, compact(st.history, cfg.context_tokens), TOOLS)
        st.step += 1
        st.spent += reply.cost
        # >> C07 tool dispatch, tool errors, malformed output
        if reply.error:
            st.malformed += 1
            log(cfg, "malformed_reply", error=reply.error, strikes=st.malformed)
            if st.malformed >= 3:
                status = "malformed_output"
                break
            st.history.append({"role": "user", "text": f"Your last reply was rejected: {reply.error}. Reply again with a valid tool call."})
            save_state(cfg, st)
            continue
        # << C07
        st.history.append({"role": "assistant", "text": reply.text, "calls": [{"name": c.name, "args": c.args} for c in reply.calls]})
        if not reply.calls:
            status = "succeeded" if st.coverage and st.coverage[-1] >= cfg.target else "below_target"
            break
        call = reply.calls[0]
        result = dispatch(cfg, tools, call)
        st.history.append({"role": "tool", "name": call.name, "result": result})
        log(cfg, "step", n=st.step, tool=call.name, ok="error" not in result, cost=round(st.spent, 4))
        if result.get("approval") in ("pending", "denied"):
            status = "awaiting_approval" if result["approval"] == "pending" else "approval_denied"
        if call.name == "run_tests" and "coverage" in result:
            st.coverage.append(result["coverage"])
        # >> C06 loop termination
        if call.name != "run_tests":
            st.recent_calls = (st.recent_calls + [json.dumps([call.name, call.args], sort_keys=True)])[-3:]
            if len(st.recent_calls) == 3 and len(set(st.recent_calls)) == 1:
                status = "stuck_loop"
        if call.name == "run_tests" and len(st.coverage) >= 3 and st.coverage[-1] <= st.coverage[-2] <= st.coverage[-3]:
            status = "no_progress"
        # << C06
        if call.name == "open_pr" and "url" in result:
            st.pr_url = result["url"]
        save_state(cfg, st)
    save_state(cfg, st)
    return {"repo": cfg.repo, "status": status, "coverage_before": st.coverage[0] if st.coverage else None, "coverage_after": st.coverage[-1] if st.coverage else None,
            "steps": st.step, "cost_usd": round(st.spent, 4), "pr": st.pr_url, "resumed": resumed, "attempt": cfg.attempt}


def main() -> int:
    cfg = Settings.from_env()
    faults = F.parse(cfg.chaos, cfg.repo)
    F.die_if_planned(faults, cfg.attempt)
    repo_dir = os.environ.get("REPO_DIR") or repos.materialise({"name": cfg.repo, "domain": cfg.domain, "seed": cfg.seed}, cfg.work_dir)
    llm = MockLLM("all", cfg.target, F.model_faults(faults), F.RateLimiter(faults)) if cfg.llm == "mock" else HttpLLM(cfg.model)
    try:
        result = run(cfg, llm, make_tools(repo_dir, faults, cfg.state_dir, cfg.repo))
    except TransientLLMError as e:
        log(cfg, "model_unavailable", error=str(e))
        print("RESULT " + json.dumps({"repo": cfg.repo, "status": "retryable", "error": str(e), "attempt": cfg.attempt}))
        return 75
    print("RESULT " + json.dumps(result))
    return 143 if result["status"] == "cancelled" else 0


if __name__ == "__main__":
    sys.exit(main())
