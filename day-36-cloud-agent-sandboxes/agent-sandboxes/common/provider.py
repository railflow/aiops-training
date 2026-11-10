"""The whole provider interface: create, exec, upload, download, destroy (plus an optional native checkout)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from common.spec import ExecResult, SandboxSpec


class ProviderError(RuntimeError):
    pass


@runtime_checkable
class Sandbox(Protocol):
    id: str

    def exec(self, command: str, *, cwd: str | None = None, env: dict | None = None, timeout_s: int | None = None) -> ExecResult: ...

    def upload(self, remote_path: str, data: bytes) -> None: ...

    def download(self, remote_path: str) -> bytes: ...

    def destroy(self) -> None: ...


@runtime_checkable
class Provider(Protocol):
    name: str

    def create(self, spec: SandboxSpec) -> Sandbox: ...
