"""ADK version of the crash lab. ADK has no server to kill: each step is a short-lived OS process that you start.

    python crash_lab.py        # run with the ADK virtualenv (google-adk 2.13.0)

Scenario 1: the agent pauses for confirmation (the process exits), a different process answers later.
Scenario 2: a process dies inside a tool call; a supervisor (this script, standing in for your Job controller) resumes it.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "py"))
import lab_common as lab  # noqa: E402


def say(msg: str) -> None:
    print(msg, flush=True)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"ASSERTION FAILED: {msg}")
    say(f"  ok: {msg}")


def process(mode: str, repo: str, lab_dir: str, **env) -> tuple[int, dict | None]:
    full = {**os.environ, "PYTHONPATH": f"{HERE}:{HERE.parent / 'py'}", "LAB_DIR": lab_dir, "LAB_STEP_MS": "50", **env}
    p = subprocess.run([sys.executable, str(HERE / "worker_process.py"), mode, repo], env=full, capture_output=True, text=True, timeout=120)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("STATUS ")), None)
    return p.returncode, json.loads(line[7:]) if line else None


def parked() -> str:
    say("\n=== ADK, pause for confirmation, answered by a different process ===")
    d = tempfile.mkdtemp(prefix="adk-lab-parked-")
    os.environ["LAB_DIR"] = d
    code, status = process("start", "billing-001", d)
    say(f"  process 1 exited with {code} and says {status}; steps done: {[e['tool'] for e in lab.events('done')]}")
    check(status["paused_for_confirmation"] is True, "the run stopped at the confirmation request and the process is gone (nothing waits in memory)")
    code, status = process("approve", "billing-001", d)
    say(f"  process 2: {status}")
    check(status["final"].startswith("finished billing-001"), "a new process answered the confirmation from the SQLite session and the run finished")
    check(len(lab.events("done", "run_tests")) == 2 and len(lab.events("done", "write_test_file")) == 1, "no finished tool ran again")
    check(len(lab.pull_requests()) == 1, "one pull request")
    return d


def step_crash() -> str:
    say("\n=== ADK, a process dies inside a tool call; a supervisor resumes the invocation ===")
    d = tempfile.mkdtemp(prefix="adk-lab-crash-")
    os.environ["LAB_DIR"] = d
    code, status = process("start", "billing-002", d, LAB_DIE_AT="write_test_file:after")
    say(f"  process 1 exited with {code} (137 = killed inside write_test_file)")
    check(code == 137, "the process died inside the tool call")
    code, status = process("resume", "billing-002", d)
    say(f"  process 2 (resume): {status}")
    check(status["paused_for_confirmation"] is True, "the resumed run continued to the confirmation request")
    code, status = process("approve", "billing-002", d)
    check(status["final"].startswith("finished billing-002"), "and finished after the approval")
    say(f"  write_test_file started {len(lab.events('start', 'write_test_file'))}x, finished {len(lab.events('done', 'write_test_file'))}x")
    check(len(lab.events("start", "write_test_file")) == 2, "the interrupted tool ran again: tools are at-least-once")
    check(len(lab.events("done", "run_tests")) == 2 and len(lab.events("done", "git_commit")) == 1, "the other tools ran once each")
    check(len(lab.pull_requests()) == 1, "one pull request")
    return d


if __name__ == "__main__":
    failed = 0
    for fn in (parked, step_crash):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            failed += 1
            say(f"  {e}")
    say("\nall scenarios held" if not failed else f"\n{failed} scenario(s) FAILED")
    sys.exit(1 if failed else 0)
