"""The Python twin of eve-app/agent/lib: the same ledger, the same fake repository and forge, the same scripted model.

Temporal and ADK both import this, so all three engines run the same scenario against the same world.
The 'model' is a function of the history, not a model, and the 'forge' is a JSON file.
"""
import json
import os
import re
import time
from pathlib import Path


def lab_dir() -> Path:
    d = Path(os.environ.get("LAB_DIR", ".lab"))
    (d / "repos").mkdir(parents=True, exist_ok=True)
    return d


def ledger(**entry) -> None:
    with open(lab_dir() / "ledger.jsonl", "a") as f:
        f.write(json.dumps({"pid": os.getpid(), **entry}) + "\n")


def events(event: str | None = None, tool: str | None = None, repo: str | None = None) -> list[dict]:
    path = lab_dir() / "ledger.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []
    return [r for r in rows if (event is None or r["event"] == event) and (tool is None or r.get("tool") == tool) and (repo is None or r.get("repo") == repo)]


def read_repo(repo: str) -> dict:
    p = lab_dir() / "repos" / f"{repo}.json"
    return json.loads(p.read_text()) if p.exists() else {"tests": [], "committed": False}


def write_repo(repo: str, state: dict) -> None:
    (lab_dir() / "repos" / f"{repo}.json").write_text(json.dumps(state))


def pull_requests() -> list[dict]:
    p = lab_dir() / "forge.json"
    return json.loads(p.read_text()) if p.exists() else []


def maybe_die(tool: str, when: str) -> None:
    """LAB_DIE_AT='tool:before|after' kills this process with exit 137 once (a marker file stops a second death)."""
    if os.environ.get("LAB_DIE_AT") != f"{tool}:{when}":
        return
    marker = lab_dir() / f"died-{tool}-{when}"
    if marker.exists():
        return
    marker.write_text("x")
    ledger(event="KILLED", tool=tool, when=when)
    os._exit(137)


def _pause() -> None:
    ms = int(os.environ.get("LAB_STEP_MS", "0"))
    if ms:
        time.sleep(ms / 1000)


def run_tests(repo: str) -> dict:
    ledger(event="start", tool="run_tests", repo=repo)
    maybe_die("run_tests", "before")
    _pause()
    coverage = min(90, 40 + 25 * len(read_repo(repo)["tests"]))
    maybe_die("run_tests", "after")
    ledger(event="done", tool="run_tests", repo=repo, coverage=coverage)
    return {"repo": repo, "coverage": coverage}


def write_test_file(repo: str) -> dict:
    ledger(event="start", tool="write_test_file", repo=repo)
    maybe_die("write_test_file", "before")
    _pause()
    state = read_repo(repo)
    path = f"tests/test_generated_{repo}.py"
    if path not in state["tests"]:
        state["tests"].append(path)
    write_repo(repo, state)
    maybe_die("write_test_file", "after")
    ledger(event="done", tool="write_test_file", repo=repo, path=path)
    return {"repo": repo, "path": path}


def git_commit(repo: str) -> dict:
    ledger(event="start", tool="git_commit", repo=repo)
    maybe_die("git_commit", "before")
    _pause()
    write_repo(repo, {**read_repo(repo), "committed": True})
    maybe_die("git_commit", "after")
    ledger(event="done", tool="git_commit", repo=repo)
    return {"repo": repo, "branch": f"agent/coverage-{repo}"}


def open_pr(repo: str) -> dict:
    ledger(event="start", tool="open_pr", repo=repo)
    maybe_die("open_pr", "before")
    _pause()
    key = f"coverage-pr:{repo}"
    prs = pull_requests()
    existing = None if os.environ.get("LAB_NO_IDEMPOTENCY") else next((p for p in prs if p["key"] == key), None)
    if not existing:
        (lab_dir() / "forge.json").write_text(json.dumps([*prs, {"repo": repo, "key": key}]))
    maybe_die("open_pr", "after")
    ledger(event="done", tool="open_pr", repo=repo, created=existing is None)
    return {"repo": repo, "key": key, "created": existing is None}


TOOLS = {"run_tests": run_tests, "write_test_file": write_test_file, "git_commit": git_commit, "open_pr": open_pr}
PLAN = ["run_tests", "write_test_file", "run_tests", "git_commit", "open_pr"]


def decide(task: str, results: list[tuple[str, bool]]) -> dict:
    """The scripted model. `results` is the history as (tool name, interrupted?) pairs, oldest first.

    It follows PLAN, and repeats a call whose result says it may not have taken effect, like the TypeScript twin.
    """
    repo = (re.search(r"repo=([\w.-]+)", task) or [None, "repo"])[1]
    done = [name for name, interrupted in results if not interrupted]
    if len(done) >= len(PLAN):
        return {"text": f"finished {repo}: {len(done)} steps done"}
    tool = PLAN[len(done)]
    return {"tool": tool, "args": {"repo": repo}}
