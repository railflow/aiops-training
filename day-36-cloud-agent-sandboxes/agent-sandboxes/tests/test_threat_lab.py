import subprocess

import pytest

from lab.scenarios import SCENARIOS, run_scenario
from mock.threats import interpret


def by_id(i):
    return next(s for s in SCENARIOS if s.id == i)


@pytest.fixture(autouse=True)
def nothing_dangerous_is_ever_executed(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError(f"a subprocess was started: {a}")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)


@pytest.mark.parametrize("s", SCENARIOS, ids=lambda s: s.id)
def test_every_scenario_is_recognised_and_runs_no_subprocess(s):
    assert interpret(s.command), "the command must be modelled, not passed to a shell"
    run_scenario(s, True)
    run_scenario(s, False)


def test_rm_rf_bare_deletes_your_files_and_sandbox_does_not():
    assert run_scenario(by_id("rm-root"), False).host_files_deleted == 6
    boxed = run_scenario(by_id("rm-root"), True)
    assert boxed.host_files_deleted == 0 and boxed.sandbox_files_deleted > 0


@pytest.mark.parametrize("sid", ["ssh-key", "env-exfil", "remote-script", "typosquat"])
def test_exfiltration_leaks_bare_and_is_contained_in_the_sandbox(sid):
    assert run_scenario(by_id(sid), False).leaked
    boxed = run_scenario(by_id(sid), True)
    assert not boxed.leaked and boxed.blocked


def test_secrets_inside_the_sandbox_are_placeholders():
    boxed = run_scenario(by_id("env-exfil"), True)
    assert set(boxed.placeholders_leaked) == {"GITHUB_TOKEN", "OPENAI_API_KEY"}
    assert not boxed.leaked


def test_fork_bomb_freezes_a_bare_machine_and_hits_the_limit_in_a_sandbox():
    assert run_scenario(by_id("fork-bomb"), False).machine_frozen
    boxed = run_scenario(by_id("fork-bomb"), True)
    assert boxed.pid_limit_hit and not boxed.machine_frozen and boxed.billed_seconds == 300


def test_other_tenants_are_unreachable_in_a_sandbox():
    assert run_scenario(by_id("other-tenant"), False).other_tenant_read
    assert not run_scenario(by_id("other-tenant"), True).other_tenant_read


@pytest.mark.parametrize("sid", ["allowed-host-exfil", "credential-abuse"])
def test_two_things_the_sandbox_does_not_solve(sid):
    s = by_id(sid)
    assert s.sandbox_solves is False
    boxed = run_scenario(s, True)
    assert boxed.leaked or boxed.credential_abused


def test_a_deny_all_policy_closes_the_allowed_host_hole():
    from common.spec import NetworkPolicy
    from lab.scenarios import lab_spec
    from mock.provider import MockProvider
    import dataclasses

    spec = dataclasses.replace(lab_spec(), network=NetworkPolicy("deny-all"))
    sb = MockProvider(isolated=True).create(spec)
    try:
        sb.exec(by_id("allowed-host-exfil").command)
        assert not sb.outcomes[-1].leaked and "api.github.com" in sb.outcomes[-1].blocked
    finally:
        sb.destroy()


def test_unknown_commands_are_not_run():
    from mock.provider import MockProvider

    sb = MockProvider().create(__import__("lab.scenarios", fromlist=["lab_spec"]).lab_spec())
    try:
        r = sb.exec("echo hello")
        assert r.exit_code == 127 and "not run" in r.stderr
    finally:
        sb.destroy()
