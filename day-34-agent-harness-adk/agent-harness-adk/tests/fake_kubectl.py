"""A stand-in for kubectl that runs each Job as a local subprocess.

Only the verbs the orchestrator uses are implemented: apply -f -, get jobs|pods, logs, delete job.
State lives in $FAKE_KUBE_STATE (a directory), so every orchestrator call (a fresh process) sees the same cluster.
Knobs: FAKE_THROTTLE=N makes the first N calls answer 429; Exit code 137 reads back as OOMKilled.
"""
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ["FAKE_KUBE_STATE"])


@contextmanager
def locked():
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / "lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def load() -> dict:
    p = STATE / "db.json"
    return json.loads(p.read_text()) if p.exists() else {"jobs": {}, "calls": 0, "peak": 0}


def save(db: dict):
    (STATE / "db.json").write_text(json.dumps(db))


def exit_code(job: dict):
    p = Path(job["dir"]) / "exit"
    return int(p.read_text()) if p.exists() else None


def start(manifest: dict) -> dict:
    name = manifest["metadata"]["name"]
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    jobdir = STATE / "jobs" / name
    jobdir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "PYTHONPATH", "LANG", "TMPDIR"}}
    for e in container["env"]:
        env[e["name"]] = e["value"].replace("/state", str(STATE / "volume")) if e["value"].startswith("/state") else e["value"]
    env["HOME"] = str(jobdir / "home")
    env["PYTHONPATH"] = str(ROOT)
    argv = [sys.executable if container["command"][0] == "python" else container["command"][0], *container["command"][1:]]
    wrapper = f"{json.dumps(argv)}"
    script = (f"import json,subprocess,sys,signal;"
              f"p=subprocess.Popen(json.loads({wrapper!r}),stdout=open({str(jobdir / 'out')!r},'w'),stderr=open({str(jobdir / 'err')!r},'w'));"
              f"signal.signal(signal.SIGTERM,lambda *a:p.send_signal(signal.SIGTERM));"
              f"c=p.wait();open({str(jobdir / 'exit')!r},'w').write(str(c if c>=0 else 128-c))")
    proc = subprocess.Popen([sys.executable, "-c", script], cwd=ROOT, env=env, start_new_session=True,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"name": name, "labels": manifest["metadata"]["labels"], "dir": str(jobdir), "pid": proc.pid, "created": time.time(), "env": {e["name"]: e["value"] for e in container["env"]}}


def job_json(job: dict) -> dict:
    code = exit_code(job)
    status = {}
    if code is None:
        status["active"] = 1
    elif code == 0:
        status["succeeded"] = 1
    else:
        status["failed"] = 1
        if job.get("deadline"):
            status["conditions"] = [{"type": "Failed", "reason": "DeadlineExceeded"}]
    return {"metadata": {"name": job["name"], "labels": job["labels"]}, "status": status}


def main(argv: list[str]) -> int:
    with locked():
        db = load()
        db["calls"] += 1
        throttle = int(os.environ.get("FAKE_THROTTLE", "0"))
        if db["calls"] <= throttle:
            save(db)
            print("Error from server (TooManyRequests): 429 Too Many Requests", file=sys.stderr)
            return 1
        args = [a for a in argv if a not in ("--ignore-not-found", "--wait=false")]
        if args[:2] == ["-n", args[1]]:
            args = args[2:]
        verb = args[0]
        if verb == "apply":
            manifest = json.loads(sys.stdin.read())
            name = manifest["metadata"]["name"]
            if name not in db["jobs"]:
                db["jobs"][name] = start(manifest)
            running = sum(1 for j in db["jobs"].values() if exit_code(j) is None)
            db["peak"] = max(db["peak"], running)
            print(f"job.batch/{name} configured")
        elif verb == "get" and args[1] == "jobs":
            selector = dict(kv.split("=") for kv in args[args.index("-l") + 1].split(","))
            items = [job_json(j) for j in db["jobs"].values() if all(j["labels"].get(k) == v for k, v in selector.items())]
            print(json.dumps({"items": items}))
        elif verb == "get" and args[1] == "pods":
            name = args[args.index("-l") + 1].split("=")[1]
            job = db["jobs"].get(name)
            if not job:
                print(json.dumps({"items": []}))
            else:
                code = exit_code(job)
                reason = "OOMKilled" if code == 137 else None
                status = {}
                status["containerStatuses"] = [{"state": {"terminated": {"exitCode": code, "reason": reason}}}] if code is not None else []
                print(json.dumps({"items": [{"status": status}]}))
        elif verb == "logs":
            job = db["jobs"].get(args[1].split("/")[1])
            print((Path(job["dir"]) / "out").read_text() if job else "", end="")
        elif verb == "delete":
            job = db["jobs"].pop(args[2], None)
            if job and exit_code(job) is None:
                try:
                    os.killpg(job["pid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if job:
                shutil.rmtree(job["dir"], ignore_errors=True)
        else:
            print(f"fake kubectl: unsupported {args}", file=sys.stderr)
            return 2
        save(db)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
