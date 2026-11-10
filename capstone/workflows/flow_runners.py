"""JobRunner: the seam between workflow code and 'where does the agent actually run'. Swap the implementation, keep the workflows.

KubernetesJobRunner shells out to kubectl (present in the worker image). LocalProcessRunner / fakes are for tests and for a laptop with no cluster.
A sandbox service (E2B-style microVM, Day 29) would be a third implementation of the same two methods.
"""
import json
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol


@dataclass
class JobOutcome:
    succeeded: bool
    logs: str
    reason: str = ""            # "", "timeout", "failed", "error"


class JobRunner(Protocol):
    def run(self, name: str, manifest: Dict, secret: Dict[str, str], timeout_s: int, heartbeat: Callable[[str], None]) -> JobOutcome: ...
    def kill(self, name: str) -> None: ...


class KubernetesJobRunner:
    def __init__(self, namespace="capstone", kubectl="kubectl", poll_s=5):
        self.ns, self.kubectl, self.poll_s = namespace, kubectl, poll_s

    def _k(self, *args, stdin=None, check=True):
        return subprocess.run([self.kubectl, "-n", self.ns, *args], input=stdin, capture_output=True, text=True, check=check)

    def run(self, name, manifest, secret, timeout_s, heartbeat):
        secret_name = f"run-{name.split('-', 1)[1]}"
        try:
            # Secrets go through stdin as a manifest: never on argv, never in a file.
            self._k("apply", "-f", "-", stdin=json.dumps({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": secret_name, "labels": {"app": "run-secret"}}, "stringData": secret}))
            self._k("apply", "-f", "-", stdin=json.dumps(manifest))
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                st = json.loads(self._k("get", "job", name, "-o", "json").stdout).get("status", {})
                heartbeat(f"{name}: active={st.get('active', 0)} succeeded={st.get('succeeded', 0)} failed={st.get('failed', 0)}")
                if st.get("succeeded"):
                    return JobOutcome(True, self._logs(name))
                if st.get("failed"):
                    return JobOutcome(False, self._logs(name), "failed")
                time.sleep(self.poll_s)
            self.kill(name)
            return JobOutcome(False, self._logs(name), "timeout")
        finally:
            self._k("delete", "secret", secret_name, "--ignore-not-found", check=False)      # the token dies with the run

    def _logs(self, name):
        return self._k("logs", f"job/{name}", "--tail=400", check=False).stdout

    def kill(self, name):
        self._k("delete", "job", name, "--ignore-not-found", "--wait=false", check=False)


class FakeRunner:
    """Test double: `script(name, manifest, secret)` returns the logs a real job would print."""

    def __init__(self, script):
        self.script, self.calls, self.killed = script, [], []

    def run(self, name, manifest, secret, timeout_s, heartbeat):
        heartbeat("fake")
        self.calls.append((name, manifest, secret))
        out = self.script(name, manifest, secret)
        return out if isinstance(out, JobOutcome) else JobOutcome(True, out)

    def kill(self, name):
        self.killed.append(name)
