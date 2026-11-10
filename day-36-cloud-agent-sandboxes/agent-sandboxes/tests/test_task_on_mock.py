import json

import pytest

from common.fake_agent import FakeAgent, GullibleAgent, functions_in, render_test_file
from common.provider import Provider, Sandbox
from common.run_task import fixture_files, load_task, run_task, spec_from_task
from mock.provider import MockProvider


@pytest.fixture
def task():
    return load_task()


def test_mock_provider_satisfies_the_interface(task):
    p = MockProvider()
    assert isinstance(p, Provider)
    sb = p.create(spec_from_task(task))
    try:
        assert isinstance(sb, Sandbox)
    finally:
        sb.destroy()


@pytest.mark.parametrize("isolated", [True, False])
def test_the_task_raises_coverage_and_returns_a_clean_diff(task, isolated):
    result = run_task(MockProvider(isolated=isolated), task)
    assert result.coverage_before == pytest.approx(55.2)
    assert result.coverage_after > 95
    assert result.diff.count("diff --git") == 1
    assert "tests/test_generated_stock.py" in result.diff
    assert "cov.py" not in result.diff and "coverage.json" not in result.diff


def test_steps_happen_in_the_documented_order(task):
    result = run_task(MockProvider(), task)
    assert [e["step"] for e in result.events] == ["create", "checkout", "upload_tools", "install", "baseline", "agent", "verify", "collect", "destroy"]


def test_the_sandbox_is_destroyed_even_when_a_step_fails(task, monkeypatch):
    p = MockProvider()

    class Broken(FakeAgent):
        def run(self, *a, **k):
            raise RuntimeError("agent crashed")

    with pytest.raises(RuntimeError):
        run_task(p, task, agent=Broken())
    assert all(sb.destroyed for sb in p.created)


def test_the_generated_file_is_valid_python_and_covers_the_missing_functions(task):
    src = fixture_files(task)["src/inventory/stock.py"].decode()
    text = render_test_file(functions_in(src))
    compile(text, "generated", "exec")
    for name in ("low_stock", "total_value", "restock_plan"):
        assert name in text


def test_a_deny_all_policy_makes_install_fail_loudly(task):
    from common.provider import ProviderError
    from common.spec import NetworkPolicy

    t = dict(task)
    spec = spec_from_task(t, network=NetworkPolicy("deny-all"))
    sample = fixture_files(t)
    assert "requirements.txt" in sample
    # the sample has no dependencies, so install succeeds even with no network: add one to see the policy bite
    p = MockProvider(isolated=True)
    sb = p.create(spec)
    try:
        sb.upload("/work/repo/requirements.txt", b"requests==2.0\n")
        r = sb.exec("python -m pip install -r requirements.txt", cwd="/work/repo")
        assert r.exit_code == 1 and "network policy" in r.stderr
    finally:
        sb.destroy()


def test_prompt_injected_agent_obeys_the_readme_but_the_sandbox_contains_it(task):
    agent = GullibleAgent()
    p = MockProvider(isolated=True)
    result = run_task(p, task, agent=agent)
    assert agent.obeyed and "collector.evil.example" in agent.obeyed[0]
    assert result.coverage_after > 95  # the real work still happens
    outcome = p.created[0].outcomes[0]
    assert not outcome.leaked and "collector.evil.example" in outcome.blocked


def test_the_same_injected_agent_on_a_bare_machine_leaks_the_key(task):
    agent = GullibleAgent()
    p = MockProvider(isolated=False)
    run_task(p, task, agent=agent)
    assert any("id_ed25519" in x for x in p.created[0].outcomes[0].leaked)


def test_task_json_and_fixture_hold_no_secret_values(task):
    blob = json.dumps(task) + "".join(v.decode() for v in fixture_files(task).values())
    for needle in ("ghp_", "sk-", "BEGIN PRIVATE KEY", "AKIA"):
        assert needle not in blob
