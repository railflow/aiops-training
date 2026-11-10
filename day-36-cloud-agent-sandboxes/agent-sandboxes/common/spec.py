"""The vocabulary shared by every provider. Nothing here can hold a secret value, only names."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NetworkPolicy:
    """mode is "allow-all", "deny-all" or "allow-list" (then `allow` lists domain names)."""

    mode: str = "allow-all"
    allow: tuple = ()

    def __post_init__(self) -> None:
        if self.mode not in ("allow-all", "deny-all", "allow-list"):
            raise ValueError(f"unknown network mode {self.mode!r}")
        if self.mode != "allow-list" and self.allow:
            raise ValueError("allow is only meaningful with mode='allow-list'")


@dataclass(frozen=True)
class SecretRef:
    """A credential the sandbox may *use*. `secret_name` is the name in the provider's or the orchestrator's secret store.

    `env_name` is the variable the code in the sandbox sees; `hosts` are the only hosts a brokering provider will send it to.
    """

    env_name: str
    secret_name: str
    hosts: tuple = ()


@dataclass(frozen=True)
class SandboxSpec:
    image: str = "python:3.12-slim"
    timeout_s: int = 300
    cpu: float = 1.0
    memory_mb: int = 1024
    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    env: dict = field(default_factory=dict)
    secrets: tuple = ()
    workdir: str = "/work/repo"
    labels: dict = field(default_factory=dict)


@dataclass
class ExecResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0
