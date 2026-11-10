"""An offline provider. Benign commands of the task really run in a temporary directory; every other command is only *modelled*.

`MockProvider(isolated=False)` is "run it on my machine". `MockProvider(isolated=True)` behaves like a sandbox with the properties the
real providers document (own filesystem, egress policy, brokered secrets, process limit, timeout). It proves nothing about any real
provider's isolation: it encodes the claims so that you can see what they would and would not change.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from common.provider import ProviderError
from common.spec import ExecResult, SandboxSpec
from mock.threats import interpret
from mock.world import BareWorld, Outcome, SandboxWorld

SAFE_GIT = {"init", "add", "commit", "diff"}
SAFE_ENV = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "HOME": "/nonexistent", "LANG": "C.UTF-8"}


class MockSandbox:
    def __init__(self, provider: "MockProvider", spec: SandboxSpec) -> None:
        self.id = f"mock-{uuid.uuid4().hex[:8]}"
        self.spec = spec
        self.provider = provider
        self.root = Path(tempfile.mkdtemp(prefix="sandbox-mock-"))
        self.world = SandboxWorld(spec) if provider.isolated else BareWorld(spec)
        self.outcomes: list = []
        self.destroyed = False
        self.created = time.monotonic()

    def path(self, remote: str) -> Path:
        p = (self.root / remote.lstrip("/")).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ProviderError(f"path escapes the sandbox: {remote}")
        return p

    def upload(self, remote_path: str, data: bytes) -> None:
        self._alive()
        p = self.path(remote_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def download(self, remote_path: str) -> bytes:
        self._alive()
        p = self.path(remote_path)
        if not p.is_file():
            raise ProviderError(f"no such file in the sandbox: {remote_path}")
        return p.read_bytes()

    def destroy(self) -> None:
        if not self.destroyed:
            shutil.rmtree(self.root, ignore_errors=True)
            self.destroyed = True

    def _alive(self) -> None:
        if self.destroyed:
            raise ProviderError("sandbox was destroyed")

    def exec(self, command: str, *, cwd: str | None = None, env: dict | None = None, timeout_s: int | None = None) -> ExecResult:
        self._alive()
        t0 = time.monotonic()
        res = self._benign(command, cwd, timeout_s or self.spec.timeout_s)
        if res is None:
            res = self._model(command)
        res.duration_s = round(time.monotonic() - t0, 3)
        return res

    def _benign(self, command: str, cwd: str | None, timeout_s: int) -> ExecResult | None:
        work = self.path(cwd or self.spec.workdir)
        parts = [p.strip() for p in command.split("&&")]
        if not all(self._is_benign(p) for p in parts):
            return None
        out, err = "", ""
        for part in parts:
            argv = shlex.split(part)
            if argv[0] == "mkdir":
                self.path(argv[-1]).mkdir(parents=True, exist_ok=True)
            elif argv[0] == "printf":
                (work / ".git" / "info").mkdir(parents=True, exist_ok=True)
                with open(work / ".git" / "info" / "exclude", "a") as f:
                    f.write(argv[1].encode().decode("unicode_escape"))
            elif argv[0] == "git":
                r = subprocess.run(["git", *argv[1:]], cwd=work, capture_output=True, text=True, env=SAFE_ENV, timeout=timeout_s)
                out, err = out + r.stdout, err + r.stderr
                if r.returncode:
                    return ExecResult(r.returncode, out, err)
            elif argv[:3] == ["python", "-m", "pip"]:
                r = self._pip(work)
                out += r.stdout
                if r.exit_code:
                    return r
            elif argv[:2] == ["python", "cov.py"]:
                r = subprocess.run([sys.executable, "cov.py"], cwd=work, capture_output=True, text=True, env=SAFE_ENV, timeout=timeout_s)
                out, err = out + r.stdout, err + r.stderr
                if r.returncode:
                    return ExecResult(r.returncode, out, err)
        return ExecResult(0, out, err)

    @staticmethod
    def _is_benign(part: str) -> bool:
        try:
            argv = shlex.split(part)
        except ValueError:
            return False
        if not argv:
            return False
        if argv[0] == "mkdir":
            return argv[1:2] == ["-p"] and len(argv) == 3 and ".." not in argv[2]
        if argv[0] == "printf":
            return len(argv) == 4 and argv[2:] == [">>", ".git/info/exclude"] and "$" not in argv[1] and "`" not in argv[1]
        if argv[0] == "git":
            return len(argv) > 1 and (argv[1] in SAFE_GIT or argv[1] == "-c") and ";" not in part and "|" not in part
        if argv[:3] == ["python", "-m", "pip"]:
            return argv[3:] == ["install", "-r", "requirements.txt"]
        return argv in (["python", "cov.py"],)

    def _pip(self, work: Path) -> ExecResult:
        req = (work / "requirements.txt").read_text() if (work / "requirements.txt").exists() else ""
        wanted = [ln.strip() for ln in req.splitlines() if ln.strip() and not ln.startswith("#")]
        if not wanted:
            return ExecResult(0, "Nothing to install (offline mock).\n")
        if not self.world.egress_allowed("pypi.org"):
            return ExecResult(1, "", "ERROR: could not reach pypi.org: network policy denies it\n")
        return ExecResult(0, "Would install: " + ", ".join(wanted) + " (offline mock, nothing downloaded)\n")

    def _model(self, command: str) -> ExecResult:
        effects = interpret(command)
        if not effects:
            out = Outcome(unknown=True)
            self.outcomes.append(out)
            return ExecResult(127, "", f"mock: command not recognised and not run: {command[:60]}\n")
        before = self.world.out
        self.world.out = Outcome()
        out = self.world.apply(effects)
        self.outcomes.append(out)
        self.world.out = before
        # A command whose network call was refused fails the way curl would; everything else is reported as a model summary.
        refused = bool(out.blocked) and not out.leaked
        return ExecResult(1 if refused else 0, out.summary() + "\n")


class MockProvider:
    def __init__(self, isolated: bool = True) -> None:
        self.isolated = isolated
        self.name = "mock-sandbox" if isolated else "mock-bare-machine"
        self.created: list = []

    def create(self, spec: SandboxSpec) -> MockSandbox:
        sb = MockSandbox(self, spec)
        self.created.append(sb)
        return sb
