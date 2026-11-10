"""Both engines run as real worker processes (the way a Job runs them) against the mock model, with every fault the catalogue lists."""
import pytest

from tests.conftest import run_worker

ENGINES = ["hand_rolled.agent_loop", "adk.run_repo"]


@pytest.mark.parametrize("module", ENGINES)
def test_clean_run_raises_coverage_and_opens_one_pr(module, worker_env):
    code, result, _ = run_worker(module, worker_env)
    assert code == 0 and result["status"] == "succeeded"
    assert result["coverage_before"] < 35 and result["coverage_after"] >= 80
    assert result["pr"] and result["cost_usd"] > 0


@pytest.mark.parametrize("module", ENGINES)
@pytest.mark.parametrize("fault", ["bad_test", "bad_tool", "malformed_json", "malformed_args", "rate_limit:3"])
def test_recoverable_faults_still_reach_the_target(module, worker_env, spec, fault):
    code, result, _ = run_worker(module, worker_env, CHAOS=f"{spec['name']}:{fault}")
    assert code == 0 and result["status"] == "succeeded", result


@pytest.mark.parametrize("module,expected", [("hand_rolled.agent_loop", "stuck_loop"), ("adk.run_repo", "no_progress")])
def test_a_stuck_model_is_stopped_without_a_pr(module, expected, worker_env, spec):
    code, result, _ = run_worker(module, worker_env, CHAOS=f"{spec['name']}:stuck")
    assert code == 0 and result["status"] == expected and result["pr"] is None


@pytest.mark.parametrize("module", ENGINES)
def test_budget_stops_the_run(module, worker_env):
    code, result, _ = run_worker(module, worker_env, BUDGET_USD="0.002")
    assert result["status"] == "budget_exhausted" and result["pr"] is None


@pytest.mark.parametrize("module", ENGINES)
def test_step_limit_stops_the_run(module, worker_env):
    code, result, _ = run_worker(module, worker_env, MAX_STEPS="4")
    assert result["status"] == "max_steps" and result["pr"] is None


@pytest.mark.parametrize("module", ENGINES)
def test_a_hung_test_run_times_out_and_the_run_recovers(module, worker_env, spec):
    code, result, _ = run_worker(module, worker_env, CHAOS=f"{spec['name']}:hang", STEP_TIMEOUT_S="2")
    assert code == 0 and result["status"] == "succeeded"


@pytest.mark.parametrize("module", ENGINES)
@pytest.mark.parametrize("mode,expected", [("deny", "approval_denied"), ("file:/nonexistent", "awaiting_approval")])
def test_no_pr_without_approval(module, worker_env, mode, expected):
    code, result, _ = run_worker(module, worker_env, APPROVAL=mode)
    assert code == 0 and result["status"] == expected and result["pr"] is None


@pytest.mark.parametrize("module", ENGINES)
def test_a_killed_worker_resumes_where_it_stopped(module, worker_env, spec):
    chaos = f"{spec['name']}:die_at_test@3"
    code, result, _ = run_worker(module, worker_env, CHAOS=chaos)
    assert code == 137 and result is None
    code, result, _ = run_worker(module, worker_env, CHAOS=chaos, ATTEMPT="2")
    assert code == 0 and result["status"] == "succeeded" and result["resumed"] is True


@pytest.mark.parametrize("module", ENGINES)
def test_oom_on_attempt_one_dies_before_any_work(module, worker_env, spec):
    code, result, _ = run_worker(module, worker_env, CHAOS=f"{spec['name']}:oom@1")
    assert code == 137 and result is None


def test_hand_rolled_small_context_is_compacted_not_fatal(worker_env, spec):
    code, result, _ = run_worker("hand_rolled.agent_loop", worker_env, CONTEXT_TOKENS="800", CHAOS=f"{spec['name']}:bad_test")
    assert code == 0 and result["status"] == "succeeded"


def test_rate_limit_that_never_clears_is_retryable(worker_env, spec):
    code, result, _ = run_worker("hand_rolled.agent_loop", worker_env, CHAOS=f"{spec['name']}:rate_limit:999")
    assert code == 75 and result["status"] == "retryable"
