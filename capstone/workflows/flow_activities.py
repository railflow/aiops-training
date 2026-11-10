"""Activities: everything with side effects. Each one is safe to retry OR is configured not to be retried (run_agent), and says which.

Wiring: `Activities(runner, ch, forge)`. Production uses KubernetesJobRunner + the ClickHouse HTTP client + Forgejo REST. Tests pass fakes.
"""
import json
import os
import string
import sys
import time
import urllib.parse
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from temporalio import activity

from flow_models import AgentResult, AgentSpec, EvalResult, EvalSpec
from flow_runners import JobOutcome

CAPSTONE = Path(__file__).resolve().parent.parent
TEMPLATES = Path(os.environ.get("TEMPLATES_DIR", CAPSTONE / "agent"))


def last_result_line(logs: str) -> Optional[dict]:
    """Jobs print exactly one `RESULT {json}` line. Logs are untrusted output of an LLM-driven process: parse defensively, never eval."""
    for ln in reversed(logs.splitlines()):
        if ln.startswith("RESULT "):
            try:
                return json.loads(ln[7:])
            except ValueError:
                return None
    return None


def slug(repo: str) -> str:
    return repo.replace("/", "-").lower()


def render(template_name: str, values: dict) -> dict:
    """Render a Job template (string.Template) and parse it. Values are escaped by being JSON-safe strings in YAML flow style: reject anything exotic."""
    import yaml
    for k, v in values.items():
        if any(c in str(v) for c in ('"', "\n", "\\", "$")):
            raise ValueError(f"refusing to render {k}={v!r}: contains a quote, newline, backslash or $")
    return yaml.safe_load(string.Template((TEMPLATES / template_name).read_text()).substitute({k: str(v) for k, v in values.items()}))


class Activities:
    def __init__(self, runner, clickhouse_insert: Callable[[str, list], None], forge=None, env: Optional[dict] = None):
        self.runner, self.insert, self.forge = runner, clickhouse_insert, forge
        self.env = env if env is not None else dict(os.environ)

    def _common(self):
        e = self.env
        return {"FORGEJO_URL": e.get("FORGEJO_URL", "http://forgejo.platform.svc.cluster.local:3000"),
                "CLICKHOUSE_URL": e.get("CLICKHOUSE_URL", "http://clickhouse.observability.svc.cluster.local:8123"),
                "CLICKHOUSE_USER": e.get("CLICKHOUSE_USER", "capstone")}

    def _hb(self, msg: str):
        try:
            activity.heartbeat(msg)
        except RuntimeError:        # not running inside an activity (unit tests)
            pass

    @activity.defn
    def measure_or_evaluate(self, spec: EvalSpec) -> EvalResult:
        """Trusted evaluation Job. Idempotent: it only reads the repo and INSERTs one immutable measurement row (a retry adds a row; the queries use the latest)."""
        values = {**self._common(), "RUN_ID": spec.run_id, "REPO_LABEL": slug(spec.repo)[:60], "DEADLINE_SECONDS": spec.deadline_seconds, "EVAL_IMAGE": self.env.get("EVAL_IMAGE", "measure:1"),
                  "REPO": spec.repo, "BRANCH": spec.branch, "AGENT_RUN_ID": spec.agent_run_id, "ITERATION": spec.iteration,
                  "PREV_COVERAGE": "" if spec.prev_coverage is None else spec.prev_coverage, "ALLOW_SRC_CHANGES": int(spec.allow_src_changes)}
        secret = {"FORGEJO_TOKEN": self.env.get("FORGEJO_READ_TOKEN", self.env.get("FORGEJO_ADMIN_TOKEN", "")), "CLICKHOUSE_PASSWORD": self.env.get("CLICKHOUSE_PASSWORD", "")}
        job = render("job-eval.yaml.tpl", values)
        out: JobOutcome = self.runner.run(f"eval-{spec.run_id}", job, secret, spec.deadline_seconds, self._hb)
        res = last_result_line(out.logs)
        if res is None:
            return EvalResult(ok=False, reasons=[f"evaluate job produced no RESULT ({out.reason or 'no output'})"])
        m = res.get("measurement") or {}
        return EvalResult(ok=bool(res.get("ok")), coverage=res.get("coverage"), tests_failed=int(m.get("tests_failed") or 0), reasons=res.get("reasons") or [res.get("reason", "")] if not res.get("ok") else [], measurement=m)

    @activity.defn
    def run_agent(self, spec: AgentSpec) -> AgentResult:
        """NOT idempotent (it spends money and pushes a branch): the workflow gives it maximum_attempts=1 and decides about retries itself.
        A per-run Forgejo token is minted and passed through a per-run Secret that the runner deletes in a finally block."""
        token = self.forge.mint_token(spec.run_id) if self.forge else self.env.get("FORGEJO_BOT_TOKEN", "")
        try:
            values = {**self._common(), "RUN_ID": spec.run_id, "REPO_LABEL": slug(spec.repo)[:60], "DEADLINE_SECONDS": spec.deadline_seconds, "AGENT_IMAGE": self.env.get("AGENT_IMAGE", "capstone-agent:1"),
                      "REPO": spec.repo, "TASK": spec.task, "TARGET_COVERAGE": spec.target_coverage, "FOCUS": spec.focus or "the modules with the lowest coverage",
                      "ISSUE_NUMBER": spec.issue_number or "", "MAX_BUDGET_USD": spec.max_budget_usd, "MAX_ISSUES": 10, "PROMPT_VERSION": spec.prompt_version,
                      "MODEL": spec.model, "OPEN_PR": 1}
            secret = {"FORGEJO_TOKEN": token, "ANTHROPIC_API_KEY": self.env.get("ANTHROPIC_API_KEY", "")}
            job = render("job-agent.yaml.tpl", values)
            out: JobOutcome = self.runner.run(f"agent-{spec.run_id}", job, secret, spec.deadline_seconds + 60, self._hb)
        finally:
            if self.forge:
                self.forge.revoke_token(spec.run_id)
        res = last_result_line(out.logs)
        if res is None:
            return AgentResult(run_id=spec.run_id, outcome="timeout" if out.reason == "timeout" else "job-failed")
        return AgentResult(run_id=spec.run_id, outcome=res.get("outcome", "job-failed"), branch=res.get("branch", ""), pr_url=res.get("pr_url", ""), commits=int(res.get("commits") or 0),
                           cost_usd=float(res.get("cost_usd") or 0), duration_s=int(res.get("duration_s") or 0), model=res.get("model", ""), prompt_version=res.get("prompt_version", ""),
                           input_tokens=int(res.get("input_tokens") or 0), output_tokens=int(res.get("output_tokens") or 0), tool_versions=res.get("tool_versions") or {})

    @activity.defn
    def record_agent_run(self, repo: str, iteration: int, r: AgentResult, accepted: bool) -> None:
        """One immutable row in capstone.agent_runs. A retry duplicates the row; dashboards use uniqExact(agent_run_id) where it matters."""
        self.insert("capstone.agent_runs", [{"agent_run_id": r.run_id, "repo": repo.split("/")[-1], "iteration": iteration, "model": r.model, "prompt_version": r.prompt_version,
                                             "tool_versions": json.dumps(r.tool_versions), "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "cost_usd": r.cost_usd,
                                             "duration_s": r.duration_s, "commits": r.commits, "outcome": r.outcome + ("+accepted" if accepted else "")}])

    @activity.defn
    def record_issues(self, repo: str, agent_run_id: str) -> int:
        """Copy the issues this run filed (found through Forgejo, via the hidden marker) into capstone.issues_filed. Idempotent enough: duplicates collapse on fingerprint."""
        if not self.forge:
            return 0
        rows = self.forge.issues_for_run(repo, agent_run_id)
        if rows:
            self.insert("capstone.issues_filed", rows)
        return len(rows)

    @activity.defn
    def post_summary(self, repo: str, text: str) -> None:
        if self.forge:
            self.forge.create_issue(repo, f"Capstone improvement summary", text, labels=["ai-found"])


def all_activities(a: Activities):
    return [a.measure_or_evaluate, a.run_agent, a.record_agent_run, a.record_issues, a.post_summary]
