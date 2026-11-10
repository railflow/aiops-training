"""Temporal version of the crash lab: kill -9 the worker at the awkward moments and check what the workflow does.

    TEMPORAL_CLI=/path/to/temporal python crash_lab.py            # needs `temporal` 1.10.0 (the dev server is inside the CLI)
"""
import asyncio
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from temporalio.client import Client

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "py"))
sys.path.insert(0, str(HERE))
import lab_common as lab  # noqa: E402
from agent_workflow import TASK_QUEUE, CoverageAgent  # noqa: E402

PORT = 7333
ADDRESS = f"127.0.0.1:{PORT}"
CLI = os.environ.get("TEMPORAL_CLI", "temporal")


def say(msg: str) -> None:
    print(msg, flush=True)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"ASSERTION FAILED: {msg}")
    say(f"  ok: {msg}")


def port_open() -> bool:
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def start_server() -> subprocess.Popen:
    p = subprocess.Popen([CLI, "server", "start-dev", "--headless", "--port", str(PORT), "--log-level", "error"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(100):
        if port_open():
            return p
        time.sleep(0.2)
    raise RuntimeError("temporal dev server did not start")


def start_worker(env: dict) -> subprocess.Popen:
    full = {**os.environ, "PYTHONPATH": f"{HERE.parent / 'py'}:{HERE}", "TEMPORAL_ADDRESS": ADDRESS, **env}
    return subprocess.Popen([sys.executable, str(HERE / "worker.py")], env=full, start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def kill9(p: subprocess.Popen) -> None:
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


async def wait_until(pred, what: str, timeout: float = 60.0):
    t = time.monotonic()
    while True:
        try:
            v = await pred()
        except Exception:
            v = None
        if v:
            return v
        if time.monotonic() - t > timeout:
            raise TimeoutError(what)
        await asyncio.sleep(0.25)


async def scenario(client: Client, name: str, worker_env: dict, die_at: str | None):
    lab_dir = tempfile.mkdtemp(prefix=f"temporal-lab-{name}-")
    os.environ["LAB_DIR"] = lab_dir
    env = {"LAB_DIR": lab_dir, "LAB_STEP_MS": "200", **worker_env}
    worker = start_worker({**env, **({"LAB_DIE_AT": die_at} if die_at else {})})
    handle = await client.start_workflow(CoverageAgent.run, f"Improve coverage. repo={name}", id=f"coverage-{name}-{int(time.time())}", task_queue=TASK_QUEUE)
    return lab_dir, env, worker, handle


async def parked(client: Client) -> None:
    say("\n=== TEMPORAL, worker killed while the workflow waits for approval ===")
    lab_dir, env, worker, handle = await scenario(client, "billing-001", {}, None)
    try:
        async def waiting():
            return (await handle.query(CoverageAgent.state))["waiting_for_approval"]
        await wait_until(waiting, "workflow never reached the approval wait")
        say(f"  workflow is waiting for a signal; steps done: {[e['tool'] for e in lab.events('done')]}")
        kill9(worker)
        say("  kill -9 on the worker")
        await asyncio.sleep(1)
        worker = start_worker(env)
        say("  new worker started (new process)")
        await wait_until(waiting, "the new worker did not replay the workflow to the approval wait")
        await handle.signal(CoverageAgent.approve, "approve")
        result = await handle.result()
        say(f"  result: {result}")
        check(len(lab.events("done", "run_tests")) == 2 and len(lab.events("done", "write_test_file")) == 1, "no finished activity ran again")
        check(len(lab.pull_requests()) == 1, "one pull request")
        done = lab.events("done")
        check(len({e["pid"] for e in done[:4]}) == 1 and done[4]["pid"] != done[0]["pid"], "the first four steps ran in the first worker; the second worker replayed them from history and only ran open_pr")
    finally:
        kill9(worker)


async def step_crash(client: Client) -> None:
    say("\n=== TEMPORAL, worker dies in the middle of an activity (after its effect, before the result was recorded) ===")
    lab_dir, env, worker, handle = await scenario(client, "billing-002", {}, "write_test_file:after")
    try:
        await wait_until(lambda: asyncio.sleep(0, any(e["event"] == "KILLED" for e in lab.events())), "the worker never died")
        say("  worker died inside write_test_file; the server is waiting for the activity timeout (5 s) before it retries")
        worker = start_worker(env)
        async def waiting():
            return (await handle.query(CoverageAgent.state))["waiting_for_approval"]
        await wait_until(waiting, "workflow did not reach approval", timeout=90)
        await handle.signal(CoverageAgent.approve, "approve")
        result = await handle.result()
        say(f"  result: {result}")
        say(f"  write_test_file started {len(lab.events('start', 'write_test_file'))}x, finished {len(lab.events('done', 'write_test_file'))}x")
        check(len(lab.events("start", "write_test_file")) == 2, "the interrupted activity ran again: activities are at-least-once")
        check(len(lab.events("done", "run_tests")) == 2 and len(lab.events("done", "git_commit")) == 1, "the other activities ran once each")
        check(len(lab.pull_requests()) == 1, "one pull request")
    finally:
        kill9(worker)


async def main() -> int:
    server = start_server()
    failed = 0
    try:
        client = await Client.connect(ADDRESS)
        for fn in (parked, step_crash):
            try:
                await fn(client)
            except Exception as e:  # noqa: BLE001
                failed += 1
                say(f"  {e}")
    finally:
        kill9(server)
    say("\nall scenarios held" if not failed else f"\n{failed} scenario(s) FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
