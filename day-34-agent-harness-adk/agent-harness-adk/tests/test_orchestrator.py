"""The fan-out against a fake kubectl that runs each Job as a local process. Real workers, mock model, injected infrastructure faults."""
import json
import os
import signal
import subprocess
import sys
import time

from common.repos import make_specs
from fanout import orchestrator as O
from tests.conftest import ROOT, kube_db


def cfg(tmp_path, **kw):
    return O.Config(ledger=str(tmp_path / "ledger.jsonl"), poll_s=0.2, **kw)


def events(capsys):
    return [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]


def test_concurrency_cap_is_respected_and_everything_finishes(tmp_path, fake_kube):
    summary = O.run(cfg(tmp_path, concurrency=2), make_specs(5))
    assert summary["finished"] == 5 and summary["by_status"] == {"succeeded": 5} and summary["prs_opened"] == 5
    assert kube_db(fake_kube)["peak"] == 2
    assert summary["avg_coverage_after"] >= 80 > summary["avg_coverage_before"]


def test_job_manifest_is_locked_down_and_bounded(tmp_path):
    job = O.render_job(cfg(tmp_path, job_deadline_s=300, ttl_s=60), make_specs(1)[0], 2)
    pod = job["spec"]["template"]["spec"]
    assert job["metadata"]["name"] == "ah-r1-billing-py-001-a2" and len(job["metadata"]["name"]) <= 63
    assert job["spec"]["backoffLimit"] == 0 and job["spec"]["activeDeadlineSeconds"] == 300 and job["spec"]["ttlSecondsAfterFinished"] == 60
    assert pod["automountServiceAccountToken"] is False and pod["securityContext"]["runAsNonRoot"] is True
    container = pod["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True and "limits" in container["resources"]
    assert "envFrom" not in container  # no secret is mounted for the mock model
    assert O.render_job(cfg(tmp_path, llm="http"), make_specs(1)[0], 1)["spec"]["template"]["spec"]["containers"][0]["envFrom"]


def test_rerun_with_the_same_ledger_starts_nothing(tmp_path, fake_kube, capsys):
    c = cfg(tmp_path, concurrency=3)
    O.run(c, make_specs(3))
    capsys.readouterr()
    again = O.run(c, make_specs(3))
    assert again["finished"] == 3 and not [e for e in events(capsys) if e["event"] == "job_started"]


def test_an_existing_job_is_adopted_not_duplicated(tmp_path, fake_kube, capsys):
    c, specs = cfg(tmp_path, concurrency=3), make_specs(3)
    kube = O.Kube(c.namespace)
    kube.apply(O.render_job(c, specs[1], 1))  # a previous orchestrator process created this one before it died
    summary = O.run(c, specs, kube)
    started = [e["repo"] for e in events(capsys) if e["event"] == "job_started"]
    assert specs[1]["name"] not in started and summary["finished"] == 3


def test_an_oom_killed_job_is_retried_once_and_succeeds(tmp_path, fake_kube, capsys):
    specs = make_specs(2)
    summary = O.run(cfg(tmp_path, chaos=f"{specs[0]['name']}:oom@1"), specs)
    assert summary["by_status"] == {"succeeded": 2} and summary["retries"] == 1
    retried = [e for e in events(capsys) if e["event"] == "repo_retry"]
    assert retried[0]["reason"] == "infrastructure:OOMKilled"
    assert O.load_ledger(str(tmp_path / "ledger.jsonl"))[specs[0]["name"]]["attempts"] == 2


def test_a_repo_that_keeps_crashing_is_a_recorded_partial_failure(tmp_path, fake_kube):
    specs = make_specs(3)
    name = specs[1]["name"]
    summary = O.run(cfg(tmp_path, max_attempts=3, retry_fraction=1.0, chaos=f"{name}:crash@1+crash@2+crash@3"), specs)
    assert summary["failed"] == [name] and summary["by_status"]["succeeded"] == 2
    assert O.load_ledger(str(tmp_path / "ledger.jsonl"))[name]["attempts"] == 3


def test_retries_are_budgeted_across_the_whole_run(tmp_path, fake_kube):
    specs = make_specs(4)
    chaos = ",".join(f"{s['name']}:crash@1" for s in specs)
    summary = O.run(cfg(tmp_path, retry_fraction=0.25, chaos=chaos, concurrency=4), specs)
    assert summary["retries"] == 1 and len(summary["failed"]) == 3  # one retry allowed for four repos; the rest fail fast


def test_api_throttling_is_absorbed(tmp_path, fake_kube, monkeypatch):
    monkeypatch.setenv("FAKE_THROTTLE", "3")
    summary = O.run(cfg(tmp_path), make_specs(1))
    assert summary["finished"] == 1 and summary["failed"] == []


def test_global_budget_skips_the_remaining_repos(tmp_path, fake_kube):
    summary = O.run(cfg(tmp_path, concurrency=1, budget_usd=0.1), make_specs(6))
    assert summary["by_status"].get("skipped_budget", 0) >= 2 and summary["by_status"]["succeeded"] >= 1


def test_failed_fraction_decides_the_exit_code(tmp_path, fake_kube, monkeypatch):
    monkeypatch.chdir(tmp_path)
    name = make_specs(4)[2]["name"]
    args = ["--count", "4", "--poll", "0.2", "--max-attempts", "1", "--chaos", f"{name}:crash@1", "--concurrency", "4"]
    assert O.main([*args, "--max-failed-fraction", "0.5", "--ledger", "a.jsonl"]) == 0
    assert O.main([*args, "--max-failed-fraction", "0.0", "--ledger", "b.jsonl", "--run-id", "r2"]) == 3


def test_sigterm_deletes_jobs_ledgers_nothing_and_a_rerun_finishes(tmp_path, fake_kube):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    cmd = [sys.executable, "-m", "fanout.orchestrator", "--count", "3", "--poll", "0.2", "--concurrency", "3", "--ledger", str(tmp_path / "l.jsonl")]
    proc = subprocess.Popen(cmd, env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline and not (fake_kube / "db.json").exists():
        time.sleep(0.1)
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=30)
    assert kube_db(fake_kube)["jobs"] == {}
    assert not (tmp_path / "l.jsonl").exists() or len(O.load_ledger(str(tmp_path / "l.jsonl"))) < 3
    assert subprocess.run(cmd, env=env, cwd=ROOT, capture_output=True, timeout=120).returncode == 0
    assert len(O.load_ledger(str(tmp_path / "l.jsonl"))) == 3


def test_budget_skipped_repos_are_picked_up_by_a_rerun(tmp_path, fake_kube):
    c = cfg(tmp_path, concurrency=1, budget_usd=0.1)
    first = O.run(c, make_specs(4))
    assert first["by_status"].get("skipped_budget", 0) >= 1
    c.budget_usd = 100.0
    second = O.run(c, make_specs(4))
    assert second["by_status"] == {"succeeded": 4}
