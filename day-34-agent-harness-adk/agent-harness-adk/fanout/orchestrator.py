"""Fan-out / fan-in: one Kubernetes Job per repository, results collected into a ledger and a summary.

This is the part that stays yours with or without an agent framework. kubectl is the only dependency:
set KUBECTL to point at another binary (the tests use a fake).
"""
import argparse
import json
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.repos import make_specs

TERMINAL = {"succeeded", "below_target", "no_progress", "stuck_loop", "max_steps", "budget_exhausted", "malformed_output", "awaiting_approval", "approval_denied", "deadline"}
RETRYABLE_EXIT = {75, 137, 143}
ENGINE_COMMAND = {"hand": ["python", "-m", "hand_rolled.agent_loop"], "adk": ["python", "-m", "adk.run_repo"]}


@dataclass
class Config:
    engine: str = "hand"
    namespace: str = "agent-harness"
    image: str = "agent-harness:dev"
    run_id: str = "r1"
    ledger: str = "results.jsonl"
    concurrency: int = 10
    max_attempts: int = 3
    retry_fraction: float = 0.3
    budget_usd: float = 5.0
    max_failed_fraction: float = 0.1
    target: float = 80.0
    job_deadline_s: int = 900
    ttl_s: int = 600
    chaos: str = ""
    approval: str = "auto"
    llm: str = "mock"
    state_hostpath: str = ""
    poll_s: float = 2.0
    extra_env: dict = field(default_factory=dict)


# >> C16 structured logging and tracing
def log(event: str, **kv):
    print(json.dumps({"ts": round(time.time(), 3), "event": event, **kv}), file=sys.stderr, flush=True)
# << C16


class Kube:
    def __init__(self, namespace: str, sleep=time.sleep):
        self.cmd = shlex.split(os.environ.get("KUBECTL", "kubectl")) + ["-n", namespace]
        self.sleep = sleep

    # >> C01 concurrency, rate limits and backoff
    def run(self, args: list[str], stdin: str | None = None, attempts: int = 5) -> str:
        """The API server throttles (429) and blips (timeouts). Back off; give up loudly."""
        for n in range(attempts):
            out = subprocess.run(self.cmd + args, input=stdin, capture_output=True, text=True)
            if out.returncode == 0:
                return out.stdout
            if not re.search(r"429|Too Many Requests|timed out|connection refused|EOF", out.stderr) or n == attempts - 1:
                raise RuntimeError(f"kubectl {' '.join(args[:2])} failed: {out.stderr.strip()[:200]}")
            self.sleep(min(30.0, 0.5 * 2 ** n) * random.uniform(0.5, 1.0))
    # << C01

    def jobs(self, run_id: str) -> dict:
        items = json.loads(self.run(["get", "jobs", "-l", f"app=agent-harness,run={run_id}", "-o", "json"]))["items"]
        return {i["metadata"]["name"]: i for i in items}

    def apply(self, manifest: dict):
        self.run(["apply", "-f", "-"], stdin=json.dumps(manifest))

    def logs(self, job: str) -> str:
        return self.run(["logs", f"job/{job}"])

    def pod_state(self, job: str) -> dict:
        pods = json.loads(self.run(["get", "pods", "-l", f"job-name={job}", "-o", "json"]))["items"]
        if not pods:
            return {"reason": "PodMissing", "exit": None}
        st = pods[0]["status"]
        term = next((c["state"]["terminated"] for c in st.get("containerStatuses", []) if "terminated" in c.get("state", {})), {})
        return {"reason": st.get("reason") or term.get("reason"), "exit": term.get("exitCode")}

    def delete(self, job: str):
        self.run(["delete", "job", job, "--ignore-not-found", "--wait=false"])


def job_name(cfg: Config, repo: str, attempt: int) -> str:
    return re.sub(r"[^a-z0-9-]", "-", f"ah-{cfg.run_id}-{repo}-a{attempt}".lower())[:63].rstrip("-")


def render_job(cfg: Config, spec: dict, attempt: int) -> dict:
    env = {"REPO_NAME": spec["name"], "REPO_DOMAIN": spec["domain"], "REPO_SEED": str(spec["seed"]), "TARGET_COVERAGE": str(cfg.target), "RUN_ID": cfg.run_id,
           "ATTEMPT": str(attempt), "CHAOS": cfg.chaos, "APPROVAL": cfg.approval, "LLM_MODE": cfg.llm, "WORK_DIR": f"/state/{cfg.run_id}/work", "STATE_DIR": f"/state/{cfg.run_id}/state", "FORGE_DIR": f"/state/{cfg.run_id}/forge",
           "HOME": "/tmp/home", **cfg.extra_env}
    labels = {"app": "agent-harness", "run": cfg.run_id, "repo": re.sub(r"[^a-z0-9-]", "-", spec["name"])[:63]}
    container = {"name": "agent", "image": cfg.image, "imagePullPolicy": "IfNotPresent", "command": ENGINE_COMMAND[cfg.engine], "workingDir": "/app",
                 "env": [{"name": k, "value": v} for k, v in env.items()],
                 "resources": {"requests": {"cpu": "100m", "memory": "192Mi"}, "limits": {"cpu": "1", "memory": "768Mi"}},
                 # >> C15 sandbox isolation and secrets
                 "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}},
                 # << C15
                 "volumeMounts": [{"name": "state", "mountPath": "/state"}, {"name": "tmp", "mountPath": "/tmp"}]}
    if cfg.llm == "http":
        # >> C15 sandbox isolation and secrets
        container["envFrom"] = [{"secretRef": {"name": "llm-credentials"}}]  # created by an admin; its value never appears in this file, args or logs
        # << C15
    # >> C12 checkpoint, resume and session persistence
    # A retry is a NEW pod. Session state and the repo working tree must outlive the pod: emptyDir only survives container restarts.
    # In production: a PVC per run, or object storage plus a database session service. The lab uses a node-local hostPath.
    state_volume = {"name": "state", "hostPath": {"path": cfg.state_hostpath, "type": "DirectoryOrCreate"}} if cfg.state_hostpath else {"name": "state", "emptyDir": {"sizeLimit": "1Gi"}}
    # << C12
    # >> C15 sandbox isolation and secrets
    pod_security = {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001, "seccompProfile": {"type": "RuntimeDefault"}}
    # << C15
    # >> C10 timeouts per step and per job
    deadline = cfg.job_deadline_s
    # << C10
    # >> C03 TTL and cleanup
    ttl = cfg.ttl_s
    # << C03
    return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": job_name(cfg, spec["name"], attempt), "namespace": cfg.namespace, "labels": labels},
            "spec": {"backoffLimit": 0, "activeDeadlineSeconds": deadline, "ttlSecondsAfterFinished": ttl,
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"restartPolicy": "Never", "automountServiceAccountToken": False, "securityContext": pod_security,
                                           "terminationGracePeriodSeconds": 30, "containers": [container],
                                           "volumes": [state_volume, {"name": "tmp", "emptyDir": {"sizeLimit": "512Mi"}}]}}}}


# >> C04 eviction, OOM and preemption
def classify(job: dict, pod: dict, result: dict | None) -> tuple[str, str]:
    """('done'|'retry'|'fail', reason). Infrastructure deaths are retried; a model that gave up honestly is not."""
    if job["status"].get("succeeded") and result and result["status"] in TERMINAL:
        return "done", result["status"]
    if result and result["status"] == "retryable":
        return "retry", "model_unavailable"
    conditions = {c.get("reason") for c in job["status"].get("conditions", [])}
    if "DeadlineExceeded" in conditions:
        return "retry", "deadline_exceeded"
    if pod["reason"] in {"Evicted", "OOMKilled", "Preempting", "PodMissing", "Shutdown", "NodeLost"} or pod["exit"] in RETRYABLE_EXIT:
        return "retry", f"infrastructure:{pod['reason'] or pod['exit']}"
    return "retry", f"crash:exit_{pod['exit']}"
# << C04


def parse_result(logs: str):
    lines = [ln for ln in logs.splitlines() if ln.startswith("RESULT ")]
    return json.loads(lines[-1][7:]) if lines else None


# >> C12 checkpoint, resume and session persistence
def load_ledger(path: str) -> dict:
    p = Path(path)
    return {r["repo"]: r for r in map(json.loads, p.read_text().splitlines())} if p.exists() else {}


def append_ledger(path: str, row: dict):
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")
        f.flush()
        os.fsync(f.fileno())
# << C12


def run(cfg: Config, specs: list[dict], kube: Kube | None = None, clock=time.monotonic, sleep=time.sleep) -> dict:
    kube = kube or Kube(cfg.namespace, sleep)
    done = load_ledger(cfg.ledger)
    # >> C12 checkpoint, resume and session persistence
    todo = [s for s in specs if s["name"] not in done]
    # << C12
    attempts = {s["name"]: 0 for s in specs}
    running: dict[str, tuple[dict, str, float]] = {}
    retry_queue: list[tuple[float, dict]] = []
    retries_used, spent, stop = 0, sum(r.get("cost_usd") or 0 for r in done.values()), {"flag": False}
    # >> C18 graceful cancellation
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    # << C18
    log("fanout_start", total=len(specs), already_done=len(done), concurrency=cfg.concurrency)
    # >> C02 idempotent job creation
    existing = kube.jobs(cfg.run_id)  # a restarted orchestrator adopts Jobs it created earlier instead of spawning duplicates
    for spec in list(todo):
        for a in range(cfg.max_attempts, 0, -1):
            if job_name(cfg, spec["name"], a) in existing:
                attempts[spec["name"]] = a
                running[spec["name"]] = (spec, job_name(cfg, spec["name"], a), clock())
                todo.remove(spec)
                break
    # << C02
    while (todo or running or retry_queue) and not stop["flag"]:
        now = clock()
        # >> C01 concurrency, rate limits and backoff
        while retry_queue and retry_queue[0][0] <= now:
            todo.insert(0, retry_queue.pop(0)[1])
        # << C01
        while todo and len(running) < cfg.concurrency:
            # >> C09 token and cost budgets
            if spent >= cfg.budget_usd:
                log("global_budget_reached", spent=round(spent, 4))
                for spec in todo:
                    done[spec["name"]] = {"repo": spec["name"], "status": "skipped_budget", "attempts": attempts[spec["name"]]}  # not ledgered: a rerun with more budget picks them up
                todo.clear()
                break
            # << C09
            spec = todo.pop(0)
            attempts[spec["name"]] += 1
            manifest = render_job(cfg, spec, attempts[spec["name"]])
            # >> C02 idempotent job creation
            kube.apply(manifest)  # apply, not create: repeating it is harmless
            # << C02
            running[spec["name"]] = (spec, manifest["metadata"]["name"], now)
            log("job_started", repo=spec["name"], job=manifest["metadata"]["name"], attempt=attempts[spec["name"]])
        jobs = kube.jobs(cfg.run_id) if running else {}
        for repo, (spec, name, started) in list(running.items()):
            job = jobs.get(name)
            # >> C10 timeouts per step and per job
            if job is None or (not job["status"].get("active") and not job["status"].get("succeeded") and not job["status"].get("failed")):
                if clock() - started > cfg.job_deadline_s * 1.5:
                    kube.delete(name)
                    job = {"status": {"failed": 1, "conditions": [{"reason": "DeadlineExceeded"}]}}
                else:
                    continue
            # << C10
            if job["status"].get("active") and not job["status"].get("succeeded") and not job["status"].get("failed"):
                continue
            result = parse_result(kube.logs(name)) if job["status"].get("succeeded") or job["status"].get("failed") else None
            verdict, reason = classify(job, kube.pod_state(name), result)
            del running[repo]
            # >> C03 TTL and cleanup
            kube.delete(name)
            # << C03
            spent += (result or {}).get("cost_usd") or 0
            if verdict == "done":
                done[repo] = {**result, "attempts": attempts[repo]}
                append_ledger(cfg.ledger, done[repo])
                log("repo_done", repo=repo, status=reason, attempts=attempts[repo])
                continue
            # >> C05 retry with a budget and exponential backoff
            budget_left = retries_used < max(1, int(cfg.retry_fraction * len(specs)))
            if attempts[repo] < cfg.max_attempts and budget_left:
                retries_used += 1
                retry_queue.append((clock() + min(60.0, 2.0 ** attempts[repo]) * random.uniform(0.5, 1.0) * cfg.poll_s, spec))
                retry_queue.sort(key=lambda x: x[0])
                log("repo_retry", repo=repo, reason=reason, attempt=attempts[repo])
            # << C05
            else:
                # >> C11 partial failures: record, move on
                done[repo] = {"repo": repo, "status": "failed", "reason": reason, "attempts": attempts[repo]}
                append_ledger(cfg.ledger, done[repo])
                log("repo_failed", repo=repo, reason=reason)
                # << C11
        if todo or running or retry_queue:
            sleep(cfg.poll_s)
    # >> C18 graceful cancellation
    if stop["flag"]:
        for _, name, _ in running.values():
            kube.delete(name)  # the pod gets SIGTERM and 30 s to checkpoint; nothing is ledgered, so a rerun resumes
        log("cancelled", still_running=len(running))
    # << C18
    return summarise(cfg, specs, done, retries_used)


# >> C13 fan-in aggregation
def summarise(cfg: Config, specs: list[dict], done: dict, retries: int) -> dict:
    rows = [done[s["name"]] for s in specs if s["name"] in done]
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    measured = [r for r in rows if r.get("coverage_before") is not None and r.get("coverage_after") is not None]
    prs = [r["pr"] for r in rows if r.get("pr")]
    failed = [r["repo"] for r in rows if r["status"] == "failed"]
    summary = {"run_id": cfg.run_id, "repos": len(specs), "finished": len(rows), "by_status": by_status, "retries": retries, "failed": failed, "prs_opened": len(prs),
               "duplicate_prs": len(prs) - len(set(prs)),
               "avg_coverage_before": round(sum(r["coverage_before"] for r in measured) / len(measured), 1) if measured else None,
               "avg_coverage_after": round(sum(r["coverage_after"] for r in measured) / len(measured), 1) if measured else None,
               "cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 4), "failed_fraction": round(len(failed) / max(1, len(specs)), 3)}
    return summary
# << C13


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=ENGINE_COMMAND, default="hand")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--namespace", default="agent-harness")
    ap.add_argument("--image", default="agent-harness:dev")
    ap.add_argument("--run-id", default="r1")
    ap.add_argument("--ledger", default="results.jsonl")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--budget-usd", type=float, default=5.0)
    ap.add_argument("--target", type=float, default=80.0)
    ap.add_argument("--chaos", default="")
    ap.add_argument("--approval", default="auto")
    ap.add_argument("--poll", type=float, default=2.0)
    ap.add_argument("--state-hostpath", default="")
    ap.add_argument("--max-failed-fraction", type=float, default=0.1)
    a = ap.parse_args(argv)
    cfg = Config(engine=a.engine, namespace=a.namespace, image=a.image, run_id=a.run_id, ledger=a.ledger, concurrency=a.concurrency, max_attempts=a.max_attempts, budget_usd=a.budget_usd,
                 target=a.target, chaos=a.chaos, approval=a.approval, poll_s=a.poll, max_failed_fraction=a.max_failed_fraction, state_hostpath=a.state_hostpath)
    summary = run(cfg, make_specs(a.count))
    print(json.dumps(summary, indent=2))
    return 0 if summary["failed_fraction"] <= cfg.max_failed_fraction else 3


if __name__ == "__main__":
    sys.exit(main())
