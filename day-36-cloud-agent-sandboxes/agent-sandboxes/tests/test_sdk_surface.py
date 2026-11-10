"""Every SDK name the real runners use must exist in the pinned SDK versions. Skipped when the SDK is not installed.

This checks names and parameters against the installed package. It does NOT prove the service behaves as documented."""
from __future__ import annotations

import inspect

import pytest

PINNED = {"modal": "1.6.3", "daytona": "0.230.0"}


def _require_pinned(dist: str) -> None:
    from importlib.metadata import PackageNotFoundError, version

    # The folders ./modal and ./daytona look like importable namespace packages, so check the installed distribution, not the import.
    try:
        installed = version(dist)
    except PackageNotFoundError:
        pytest.skip(f"{dist} is not installed (pip install -r requirements.txt to run this check)")
    if installed != PINNED[dist]:
        pytest.skip(f"{dist} {installed} is installed; this check is only meaningful for the pinned {PINNED[dist]}")


def test_modal_sdk_surface():
    _require_pinned("modal")
    import modal
    from modal.sandbox._sandbox import _Sandbox  # the implementation class behind the synchronous modal.Sandbox wrapper

    params = set(inspect.signature(_Sandbox.create).parameters)
    for name in ("timeout", "cpu", "memory", "env", "secrets", "block_network", "outbound_domain_allowlist", "runtime", "image", "app"):
        assert name in params, f"modal.Sandbox.create lost {name!r}"
    for attr in ("exec", "filesystem", "terminate", "tunnels", "snapshot_filesystem"):
        assert hasattr(modal.Sandbox, attr), f"modal.Sandbox lost {attr!r}"
    assert hasattr(modal.App, "lookup") and hasattr(modal.Secret, "from_name") and hasattr(modal.Image, "debian_slim")


def test_daytona_sdk_surface():
    _require_pinned("daytona")
    from daytona import CreateSandboxFromSnapshotParams, Daytona, Sandbox

    _require_pinned("daytona")
    fields = set(CreateSandboxFromSnapshotParams.model_fields)
    for name in ("language", "labels", "env_vars", "secrets", "ephemeral", "ttl_minutes", "network_block_all", "domain_allow_list", "network_allow_list", "auto_stop_interval", "snapshot"):
        assert name in fields, f"CreateSandboxFromSnapshotParams lost {name!r}"
    for attr in ("process", "fs", "git", "get_preview_link", "create_snapshot", "fork"):
        assert hasattr(Sandbox, attr), f"Sandbox lost {attr!r}"
    assert {"create", "delete"} <= set(dir(Daytona))
    from daytona._sync.filesystem import FileSystem
    from daytona._sync.git import Git
    from daytona._sync.process import Process

    assert {"cwd", "env", "timeout"} <= set(inspect.signature(Process.exec).parameters)
    assert {"branch", "username", "password"} <= set(inspect.signature(Git.clone).parameters)
    assert hasattr(FileSystem, "upload_file") and hasattr(FileSystem, "download_file")
