"""One task, any provider: checkout, upload tools, install, baseline coverage, agent writes a test, verify, collect the diff."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.fake_agent import FakeAgent
from common.provider import Provider, ProviderError, Sandbox
from common.spec import NetworkPolicy, SandboxSpec

ROOT = Path(__file__).resolve().parent.parent


def load_task(path: Path | None = None) -> dict:
    return json.loads((path or ROOT / "task" / "task.json").read_text())


def spec_from_task(task: dict, **overrides) -> SandboxSpec:
    net = task["network"]
    values = dict(
        timeout_s=task["limits"]["timeout_s"], cpu=task["limits"]["cpu"], memory_mb=task["limits"]["memory_mb"],
        network=NetworkPolicy(net["mode"], tuple(net.get("allow", ()))), workdir=task["workdir"], labels={"task": task["name"]},
    )
    values.update(overrides)
    return SandboxSpec(**values)


def fixture_files(task: dict) -> dict:
    base = ROOT / task["repo"]["fixture"]
    return {str(p.relative_to(base)): p.read_bytes() for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.name != "coverage.json"}


@dataclass
class TaskResult:
    provider: str
    sandbox_id: str
    coverage_before: float
    coverage_after: float
    diff: str
    events: list = field(default_factory=list)
    agent: dict = field(default_factory=dict)
    seconds: float = 0.0


def _must(result, what: str):
    if not result.ok:
        raise ProviderError(f"{what} failed with exit code {result.exit_code}: {result.stderr.strip() or result.stdout.strip()}")
    return result


def run_task(provider: Provider, task: dict, agent=None, spec: SandboxSpec | None = None, keep: bool = False) -> TaskResult:
    agent = agent or FakeAgent()
    spec = spec or spec_from_task(task)
    wd = task["workdir"]
    started = time.monotonic()
    events: list = []

    def note(step: str, **kv):
        events.append({"step": step, "t": round(time.monotonic() - started, 3), **kv})

    sandbox: Sandbox = provider.create(spec)
    note("create", sandbox=sandbox.id)
    try:
        repo_url = os.environ.get(task["repo"]["url_env"])
        if repo_url and hasattr(sandbox, "checkout"):
            sandbox.checkout(repo_url, wd, task["repo"]["ref"])
            note("checkout", source="git", url=repo_url)
        elif repo_url:
            _must(sandbox.exec(f"git clone --depth 1 --branch {task['repo']['ref']} {repo_url} {wd}"), "git clone")
            note("checkout", source="git", url=repo_url)
        else:
            _must(sandbox.exec(f"mkdir -p {wd}"), "mkdir")
            for rel, data in fixture_files(task).items():
                sandbox.upload(f"{wd}/{rel}", data)
            _must(sandbox.exec("git init -q . && git add -A && git -c user.email=lab@example.invalid -c user.name=lab commit -q -m initial", cwd=wd), "git init")
            note("checkout", source="fixture", files=len(fixture_files(task)))
        _must(sandbox.exec("printf 'cov.py\\ncoverage.json\\n__pycache__/\\n' >> .git/info/exclude", cwd=wd), "git exclude")
        sandbox.upload(f"{wd}/cov.py", (ROOT / "task" / "tools" / "cov.py").read_bytes())
        note("upload_tools")
        _must(sandbox.exec(task["commands"]["install"], cwd=wd), "install")
        note("install")
        base = _must(sandbox.exec(task["commands"]["coverage"], cwd=wd), "baseline tests")
        before = json.loads(sandbox.download(f"{wd}/coverage.json").decode())["percent"]
        note("baseline", coverage=before, output=base.stdout.strip())
        info = agent.run(sandbox, wd, task["agent_target_files"][0])
        note("agent", **info)
        after_run = _must(sandbox.exec(task["commands"]["coverage"], cwd=wd), "verification tests")
        after = json.loads(sandbox.download(f"{wd}/coverage.json").decode())["percent"]
        note("verify", coverage=after, output=after_run.stdout.strip())
        diff = _must(sandbox.exec(task["commands"]["diff"], cwd=wd), "git diff").stdout
        note("collect", diff_bytes=len(diff))
        return TaskResult(provider.name, sandbox.id, before, after, diff, events, info, round(time.monotonic() - started, 3))
    finally:
        if not keep:
            sandbox.destroy()
            note("destroy")
