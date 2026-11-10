"""Daytona Sandboxes behind the shared provider interface.

Written against daytona 0.230.0 (see tests/test_sdk_surface.py). NOT run against a live account.
Auth: DAYTONA_API_KEY (optional DAYTONA_API_URL and DAYTONA_TARGET).
"""
from __future__ import annotations

import math
import posixpath
import time

from common.provider import ProviderError
from common.spec import ExecResult, SandboxSpec


def create_params_kwargs(spec: SandboxSpec) -> dict:
    """Map the neutral spec to CreateSandboxFromSnapshotParams fields (pure, so it can be tested offline)."""
    kwargs: dict = {
        "language": "python",
        "labels": dict(spec.labels),
        "ephemeral": True,
        "ttl_minutes": max(1, math.ceil(spec.timeout_s / 60)),
    }
    if spec.env:
        kwargs["env_vars"] = dict(spec.env)
    if spec.secrets:
        # Secret NAMES only: each env var inside the sandbox holds a placeholder; Daytona's proxy swaps in the value for allowed hosts.
        kwargs["secrets"] = {s.env_name: s.secret_name for s in spec.secrets}
    if spec.network.mode == "deny-all":
        kwargs["network_block_all"] = True
    elif spec.network.mode == "allow-list":
        # Comma-separated string. An allow list also blocks "essential services" (GitHub, npm, PyPI) unless they are listed.
        kwargs["domain_allow_list"] = ",".join(spec.network.allow)
    return kwargs


class DaytonaSandbox:
    def __init__(self, client, sandbox) -> None:
        self._client = client
        self._sb = sandbox
        self.id = sandbox.id

    def exec(self, command: str, *, cwd: str | None = None, env: dict | None = None, timeout_s: int | None = None) -> ExecResult:
        started = time.monotonic()
        # process.exec returns one combined `result` string, so stderr is not separate here.
        res = self._sb.process.exec(command, cwd=cwd, env=env, timeout=timeout_s)
        return ExecResult(res.exit_code, res.result or "", "", time.monotonic() - started)

    def upload(self, remote_path: str, data: bytes) -> None:
        self.exec(f"mkdir -p {posixpath.dirname(remote_path)}")
        self._sb.fs.upload_file(data, remote_path)

    def download(self, remote_path: str) -> bytes:
        data = self._sb.fs.download_file(remote_path)
        if data is None:
            raise ProviderError(f"no such file in the sandbox: {remote_path}")
        return data

    def checkout(self, url: str, path: str, ref: str) -> None:
        self._sb.git.clone(url, path, branch=ref)

    def destroy(self) -> None:
        self._client.delete(self._sb)


class DaytonaProvider:
    name = "daytona"

    def create(self, spec: SandboxSpec) -> DaytonaSandbox:
        try:
            from daytona import CreateSandboxFromSnapshotParams, Daytona
        except ImportError as exc:
            raise ProviderError("the daytona SDK is not installed (this folder is not it): pip install -r requirements.txt") from exc

        client = Daytona()
        try:
            sandbox = client.create(CreateSandboxFromSnapshotParams(**create_params_kwargs(spec)))
        except Exception as exc:  # the SDK raises several error types; surface one
            raise ProviderError(f"daytona could not create the sandbox: {exc}") from exc
        return DaytonaSandbox(client, sandbox)
