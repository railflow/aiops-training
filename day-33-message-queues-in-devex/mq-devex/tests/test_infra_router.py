"""Lab 3: the routing rules (pure), then the whole path through the REAL `./platform request` CLI against a real nats-server."""
import asyncio
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

import devbus
import router
import terraform_runner
import human_desk

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = ROOT.parent / "platform" / "platform"
CFG = router.load_routes()


@pytest.mark.parametrize("data,action,route", [
    ({"kind": "k8s-namespace-rds", "env": "dev", "name": "orders", "owner": "a"}, "automate", "namespace-with-database-nonprod"),
    ({"kind": "k8s-namespace-rds", "env": "prod", "name": "orders", "owner": "a"}, "human", "namespace-with-database-prod"),
    ({"kind": "aws-account", "name": "x", "owner": "a"}, "human", "new-cloud-account"),
    ({"kind": "dns-record", "name": "x", "owner": "a"}, "automate", "dns-record"),
    ({"kind": "teleporter", "name": "x", "owner": "a"}, "reject", "default"),
    ({"kind": "dns-record", "name": "x"}, "reject", "dns-record"),
])
def test_decide(data, action, route):
    d = router.decide(data, CFG)
    assert (d["action"], d["route"]) == (action, route)


def test_missing_fields_are_named():
    assert "owner" in router.decide({"kind": "dns-record", "name": "x"}, CFG)["reason"]


class Workers:
    """Run the router, runner and desk in a background thread, like three pods would run."""

    def __init__(self, url, state_dir):
        self.url, self.state_dir = url, state_dir
        self.loop = asyncio.new_event_loop()
        self.stop = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())

    async def _main(self):
        self.stop = asyncio.Event()
        nc, js = await devbus.connect(self.url)
        kw = dict(js=js, state_dir=self.state_dir, stop=self.stop)
        await asyncio.gather(
            devbus.run_worker("router", "infra.request.>", router.handle, **kw),
            devbus.run_worker("terraform-runner", "infra.work.terraform", terraform_runner.handle, **kw),
            devbus.run_worker("desk-tickets", "infra.human.>", human_desk.on_ticket, **kw),
            devbus.run_worker("desk-approvals", "infra.approval.*", human_desk.on_action, **kw),
            devbus.run_worker("desk-completions", "infra.completion.*", human_desk.on_action, **kw))
        await nc.close()

    def __enter__(self):
        self.thread.start()
        import time
        time.sleep(1.0)
        return self

    def __exit__(self, *a):
        self.loop.call_soon_threadsafe(self.stop.set)
        self.thread.join(timeout=10)


def platform(url, *args, env_extra=None):
    env = {**os.environ, "NATS_URL": url, "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"], "USER": "tester"}
    env.update(env_extra or {})
    return subprocess.run([str(PLATFORM), "request", *args], capture_output=True, text=True, env=env, timeout=60)


@pytest.fixture(autouse=True)
def fast(monkeypatch, tmp_path):
    monkeypatch.setenv("TF_SECONDS", "0.1")
    monkeypatch.setenv("TICKETS_FILE", str(tmp_path / "tickets.jsonl"))


def test_kinds_lists_routes(nats_url):
    r = platform(nats_url, "kinds")
    assert r.returncode == 0 and "k8s-namespace-rds" in r.stdout and "aws-account" in r.stdout


def test_automated_path_end_to_end(nats_url, state_dir):
    with Workers(nats_url, state_dir):
        r = platform(nats_url, "k8s-namespace-rds", "--name", "orders", "--owner", "alice", "--env", "dev", "--id", "req-auto-1", "--wait", "--timeout", "30")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "routed" in r.stdout and "done" in r.stdout and "orders-dev" in r.stdout


def test_prod_waits_for_human_then_runs_automation(nats_url, state_dir, tmp_path):
    with Workers(nats_url, state_dir):
        r = platform(nats_url, "k8s-namespace-rds", "--name", "orders", "--owner", "alice", "--env", "prod", "--id", "req-prod-1", "--wait", "--timeout", "30")
        assert "waiting-on-human" in r.stdout and r.returncode == 0
        assert "req-prod-1" in (tmp_path / "tickets.jsonl").read_text()
        a = platform(nats_url, "approve", "req-prod-1", "--by", "bob")
        assert a.returncode == 0
        import time
        for _ in range(40):
            s = platform(nats_url, "status", "req-prod-1")
            if "done" in s.stdout:
                break
            time.sleep(0.5)
    assert "approved" in s.stdout and "done" in s.stdout and "orders-prod" in s.stdout


def test_human_does_it_by_hand(nats_url, state_dir):
    with Workers(nats_url, state_dir):
        platform(nats_url, "aws-account", "--name", "sandbox-7", "--owner", "carol", "--id", "req-acct-1")
        import time
        time.sleep(1.5)
        platform(nats_url, "complete", "req-acct-1", "--by", "dana")
        for _ in range(40):
            s = platform(nats_url, "status", "req-acct-1")
            if "human:dana" in s.stdout:
                break
            time.sleep(0.5)
    assert "waiting-on-human" in s.stdout and "human:dana" in s.stdout


def test_unknown_kind_and_failed_apply(nats_url, state_dir):
    with Workers(nats_url, state_dir):
        r = platform(nats_url, "teleporter", "--name", "x", "--owner", "a", "--id", "req-bad-1", "--wait", "--timeout", "20")
        assert r.returncode == 1 and "rejected" in r.stdout and "platform request kinds" in r.stdout
        f = platform(nats_url, "dns-record", "--name", "x", "--owner", "a", "--id", "req-fail-1", "--set", "fail=true", "--wait", "--timeout", "20")
    assert f.returncode == 1 and "failed" in f.stdout and "quota exceeded" in f.stdout


def test_resubmitting_the_same_id_does_not_duplicate(nats_url, state_dir):
    with Workers(nats_url, state_dir):
        for _ in range(2):
            platform(nats_url, "dns-record", "--name", "x", "--owner", "a", "--id", "req-same-1")
        import time
        time.sleep(2)
        s = platform(nats_url, "status", "req-same-1")
    assert s.stdout.count("done") == 1 and s.stdout.count("routed") == 1
