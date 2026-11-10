"""The Modal and Daytona providers, driven by hand-written fakes that mimic the SDK shapes. Proves the mapping and the call
sequence, not that the real services behave this way (they were not reachable; see README)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from common.fake_agent import FakeAgent, functions_in, render_test_file
from common.real import load_provider_module
from common.spec import NetworkPolicy, SandboxSpec, SecretRef

ROOT = Path(__file__).resolve().parents[1]


def test_scripted_agent_file_matches_the_checked_in_copy_used_by_the_typescript_runner():
    src = (ROOT / "task/sample-repo/src/inventory/stock.py").read_text()
    expected = (ROOT / "task/expected/test_generated_stock.py").read_text()
    assert render_test_file(functions_in(src)) == expected


def test_modal_create_kwargs_cover_every_network_mode_and_never_hold_values():
    mod = load_provider_module("modal")
    base = SandboxSpec(timeout_s=120, cpu=1, memory_mb=512)
    assert mod.create_kwargs(base)["timeout"] == 120
    assert "block_network" not in mod.create_kwargs(base)
    assert mod.create_kwargs(SandboxSpec(network=NetworkPolicy("deny-all")))["block_network"] is True
    allow = mod.create_kwargs(SandboxSpec(network=NetworkPolicy("allow-list", ("pypi.org", "github.com"))))
    assert allow["outbound_domain_allowlist"] == ["pypi.org", "github.com"]


def test_daytona_params_map_secrets_by_name_and_allow_lists_as_a_comma_string():
    mod = load_provider_module("daytona")
    spec = SandboxSpec(timeout_s=300, network=NetworkPolicy("allow-list", ("pypi.org", "github.com")),
                       secrets=(SecretRef("GITHUB_TOKEN", "github-token", ("api.github.com",)),))
    kw = mod.create_params_kwargs(spec)
    assert kw["domain_allow_list"] == "pypi.org,github.com"
    assert kw["secrets"] == {"GITHUB_TOKEN": "github-token"}
    assert kw["ttl_minutes"] == 5 and kw["ephemeral"] is True
    assert mod.create_params_kwargs(SandboxSpec(network=NetworkPolicy("deny-all")))["network_block_all"] is True
    assert "domain_allow_list" not in mod.create_params_kwargs(SandboxSpec())


class FakeDaytonaSandbox:
    id = "fake-daytona"

    def __init__(self):
        self.files, self.commands = {}, []
        self.process = SimpleNamespace(exec=self._exec)
        self.fs = SimpleNamespace(upload_file=lambda data, dst: self.files.__setitem__(dst, data), download_file=lambda p: self.files.get(p))
        self.git = SimpleNamespace(clone=lambda url, path, branch=None: self.commands.append(f"clone {url}@{branch}"))

    def _exec(self, command, cwd=None, env=None, timeout=None):
        self.commands.append(command)
        if command == "python cov.py":
            pct = 55.2 if "before" not in self.files else 100.0
            self.files["before"] = b"1"
            self.files[f"{cwd}/coverage.json"] = json.dumps({"percent": pct}).encode()
        return SimpleNamespace(exit_code=0, result="diff --git a/x b/x" if "diff" in command else "")


def test_daytona_adapter_runs_the_common_task_against_a_fake_sdk():
    from common.run_task import load_task, run_task

    mod = load_provider_module("daytona")
    deleted = []
    fake_sb = FakeDaytonaSandbox()
    client = SimpleNamespace(delete=lambda sb: deleted.append(sb.id))

    class Provider(mod.DaytonaProvider):
        def create(self, spec):
            return mod.DaytonaSandbox(client, fake_sb)

    result = run_task(Provider(), load_task())
    assert (result.coverage_before, result.coverage_after) == (55.2, 100.0)
    assert deleted == ["fake-daytona"]
    assert "/work/repo/tests/test_generated_stock.py" in fake_sb.files


def test_modal_adapter_maps_exec_and_filesystem_calls():
    mod = load_provider_module("modal")
    calls = []
    reader = lambda text: SimpleNamespace(read=lambda: text)  # noqa: E731
    sb = SimpleNamespace(
        object_id="sb-123",
        exec=lambda *a, **k: (calls.append((a, k)), SimpleNamespace(stdout=reader("out"), stderr=reader("err"), wait=lambda: 3))[1],
        filesystem=SimpleNamespace(write_bytes=lambda data, path: calls.append(("write", path, data)), read_bytes=lambda p: b"data"),
        terminate=lambda: calls.append("terminate"),
    )
    adapter = mod.ModalSandbox(sb)
    res = adapter.exec("echo hi", cwd="/work", timeout_s=5)
    assert (res.exit_code, res.stdout, res.stderr) == (3, "out", "err")
    assert calls[0] == (("bash", "-lc", "echo hi"), {"workdir": "/work", "timeout": 5})
    adapter.upload("/a/b", b"x")
    assert adapter.download("/a/b") == b"data"
    adapter.destroy()
    assert calls[-1] == "terminate" and ("write", "/a/b", b"x") in calls


def test_real_runs_refuse_without_explicit_opt_in(monkeypatch, capsys):
    from common.real import main

    monkeypatch.delenv("SANDBOX_ALLOW_REAL", raising=False)
    assert main("modal") == 2 and "SANDBOX_ALLOW_REAL=1" in capsys.readouterr().out
    assert main("daytona") == 2
