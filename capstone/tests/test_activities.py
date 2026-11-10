import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "workflows"))
from flow_activities import Activities, last_result_line, render  # noqa: E402
from flow_models import AgentResult, AgentSpec, EvalSpec  # noqa: E402
from flow_runners import FakeRunner, JobOutcome  # noqa: E402


class FakeForge:
    def __init__(self):
        self.minted, self.revoked = [], []

    def mint_token(self, run_id):
        self.minted.append(run_id)
        return "tok-" + run_id

    def revoke_token(self, run_id):
        self.revoked.append(run_id)

    def issues_for_run(self, repo, run_id):
        return [{"repo": "a", "issue_number": 3, "fingerprint": "ff", "title": "t", "severity": "high", "category": "x", "agent_run_id": run_id, "failing_test": "t1", "file": "a.py", "line": 4, "state": "open"}]


def make(script):
    rows = []
    r = FakeRunner(script)
    return Activities(r, lambda table, data: rows.append((table, data)), FakeForge(), env={"AGENT_IMAGE": "img:1"}), r, rows


def test_result_line_parsing_ignores_noise_and_garbage():
    assert last_result_line("hello\nRESULT {\"a\": 1}\nbye") == {"a": 1}
    assert last_result_line("RESULT {not json") is None
    assert last_result_line("no result here") is None


def test_run_agent_renders_a_hardened_job_mints_and_always_revokes_the_token():
    logs = 'RESULT ' + json.dumps({"outcome": "pushed", "branch": "ai/coverage-x", "cost_usd": 1.25, "commits": 2, "model": "m", "duration_s": 90})
    a, runner, _ = make(lambda n, m, s: logs)
    res = a.run_agent(AgentSpec(repo="capstone/a", run_id="a-i1-abc", iteration=1))
    assert isinstance(res, AgentResult) and res.outcome == "pushed" and res.cost_usd == 1.25 and res.commits == 2
    name, job, secret = runner.calls[0]
    pod = job["spec"]["template"]["spec"]
    c = pod["containers"][0]
    assert name == "agent-a-i1-abc" and job["spec"]["backoffLimit"] == 0 and job["spec"]["activeDeadlineSeconds"] == 1800
    assert pod["automountServiceAccountToken"] is False and c["securityContext"]["readOnlyRootFilesystem"] is True
    assert pod["securityContext"]["runAsNonRoot"] is True and c["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    assert secret["FORGEJO_TOKEN"] == "tok-a-i1-abc" and "FORGEJO_TOKEN" not in json.dumps(job)       # the token is in the Secret only, never in the Job spec
    assert a.forge.revoked == ["a-i1-abc"]


def test_token_is_revoked_even_when_the_job_blows_up():
    def boom(n, m, s):
        raise RuntimeError("kubectl exploded")
    a, _, _ = make(boom)
    with pytest.raises(RuntimeError):
        a.run_agent(AgentSpec(repo="capstone/a", run_id="r1", iteration=1))
    assert a.forge.revoked == ["r1"]


def test_agent_without_a_result_line_is_a_job_failure_not_a_crash():
    a, _, _ = make(lambda n, m, s: JobOutcome(False, "segfault", "failed"))
    assert a.run_agent(AgentSpec(repo="capstone/a", run_id="r1", iteration=1)).outcome == "job-failed"
    a, _, _ = make(lambda n, m, s: JobOutcome(False, "", "timeout"))
    assert a.run_agent(AgentSpec(repo="capstone/a", run_id="r2", iteration=1)).outcome == "timeout"


def test_evaluate_parses_the_result_and_hides_nothing():
    logs = "RESULT " + json.dumps({"ok": False, "reasons": ["coverage dropped 40 -> 30"], "coverage": 30.0, "measurement": {"tests_failed": 1}})
    a, runner, _ = make(lambda n, m, s: logs)
    ev = a.measure_or_evaluate(EvalSpec(repo="capstone/a", run_id="r1-ev", branch="ai/x", iteration=1, prev_coverage=40.0))
    assert ev.ok is False and ev.coverage == 30.0 and ev.reasons == ["coverage dropped 40 -> 30"] and ev.tests_failed == 1
    assert runner.calls[0][1]["spec"]["template"]["metadata"]["labels"]["app"] == "evaluate"


def test_records_use_the_short_repo_name_and_the_issue_rows_come_from_forgejo():
    a, _, rows = make(lambda n, m, s: "")
    a.record_agent_run(repo="capstone/billing", iteration=2, r=AgentResult(run_id="r1", outcome="pushed", cost_usd=1.5), accepted=True)
    assert a.record_issues("capstone/billing", "r1") == 1
    assert rows[0][0] == "capstone.agent_runs" and rows[0][1][0]["repo"] == "billing" and rows[0][1][0]["outcome"] == "pushed+accepted"
    assert rows[1][0] == "capstone.issues_filed" and rows[1][1][0]["agent_run_id"] == "r1"


def test_render_refuses_values_that_could_break_out_of_the_yaml():
    with pytest.raises(ValueError):
        render("job-agent.yaml.tpl", {"FOCUS": 'x"\n  injected: true'})
