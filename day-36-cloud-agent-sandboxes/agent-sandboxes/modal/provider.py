"""Modal Sandboxes behind the shared provider interface.

Written against modal 1.6.3 (see tests/test_sdk_surface.py). NOT run against a live account.
Auth: MODAL_TOKEN_ID and MODAL_TOKEN_SECRET (or `modal setup`).
"""
from __future__ import annotations

import os
import time

from common.provider import ProviderError
from common.spec import ExecResult, SandboxSpec

APP_NAME = "agent-sandboxes-lab"


def create_kwargs(spec: SandboxSpec) -> dict:
    """Map the neutral spec to modal.Sandbox.create keyword arguments (pure, so it can be tested offline)."""
    kwargs: dict = {"timeout": spec.timeout_s, "cpu": spec.cpu, "memory": spec.memory_mb}
    if spec.env:
        kwargs["env"] = dict(spec.env)
    if spec.network.mode == "deny-all":
        kwargs["block_network"] = True
    elif spec.network.mode == "allow-list":
        kwargs["outbound_domain_allowlist"] = list(spec.network.allow)
    runtime = os.environ.get("MODAL_SANDBOX_RUNTIME")
    if runtime:
        kwargs["runtime"] = runtime
    return kwargs


class ModalSandbox:
    def __init__(self, sb) -> None:
        self._sb = sb
        self.id = sb.object_id

    def exec(self, command: str, *, cwd: str | None = None, env: dict | None = None, timeout_s: int | None = None) -> ExecResult:
        started = time.monotonic()
        extra: dict = {}
        if cwd:
            extra["workdir"] = cwd
        if env:
            extra["env"] = env
        if timeout_s:
            extra["timeout"] = timeout_s
        proc = self._sb.exec("bash", "-lc", command, **extra)
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        code = proc.wait()
        return ExecResult(code, stdout, stderr, time.monotonic() - started)

    def upload(self, remote_path: str, data: bytes) -> None:
        self._sb.filesystem.write_bytes(data, remote_path)

    def download(self, remote_path: str) -> bytes:
        return self._sb.filesystem.read_bytes(remote_path)

    def destroy(self) -> None:
        self._sb.terminate()


class ModalProvider:
    name = "modal-sandbox"

    def __init__(self, app_name: str = APP_NAME) -> None:
        self.app_name = app_name

    def create(self, spec: SandboxSpec) -> ModalSandbox:
        import modal

        if not hasattr(modal, "Sandbox"):
            raise ProviderError("the modal SDK is not installed (this folder is not it): pip install -r requirements.txt")
        app = modal.App.lookup(self.app_name, create_if_missing=True)
        image = modal.Image.debian_slim(python_version="3.12").apt_install("git")
        kwargs = create_kwargs(spec)
        if spec.secrets:
            # Secrets are created ahead of time (`modal secret create ...`) and arrive as plain environment variables inside the sandbox.
            kwargs["secrets"] = [modal.Secret.from_name(s.secret_name) for s in spec.secrets]
        try:
            sb = modal.Sandbox.create(app=app, image=image, **kwargs)
        except Exception as exc:  # the SDK raises several error types; surface one
            raise ProviderError(f"modal could not create the sandbox: {exc}") from exc
        return ModalSandbox(sb)
