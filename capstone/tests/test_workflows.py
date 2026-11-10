"""Orchestration tests with the Temporal time-skipping test server (downloaded once by the SDK) and FAKE activities of the same names.
They check decisions (stop reasons, budgets, approval, pause, bounded fan-out), not the agent. Activities are tested separately with a FakeRunner."""
import asyncio
import sys
import uuid
from pathlib import Path

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "workflows"))
from flow_models import AgentResult, EvalResult, FleetInput, FleetSummary, RepoInput, RepoSummary  # noqa: E402
from flow_workflows import ImproveFleetWorkflow, ImproveRepoWorkflow  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stub_repo_workflow import StubRepo  # noqa: E402

Q = "capstone-test"
pytestmark = pytest.mark.asyncio


class Fakes:
    """Scripted world: coverage after each iteration, and a log of what the workflow asked for."""

    def __init__(self, baseline=10.0, gains=(15.0, 15.0, 15.0, 15.0), cost=1.0, outcomes=None, eval_ok=True):
        self.baseline, self.gains, self.cost, self.eval_ok = baseline, list(gains), cost, eval_ok
        self.outcomes = outcomes or {}
        self.calls, self.cov, self.n = [], baseline, 0
        self.running = self.peak = 0

    def activities(self):
        f = self

        @activity.defn(name="measure_or_evaluate")
        async def ev(spec) -> EvalResult:
            f.calls.append(("eval", spec["branch"] if isinstance(spec, dict) else spec.branch))
            if (spec["iteration"] if isinstance(spec, dict) else spec.iteration) == 0:
                return EvalResult(ok=True, coverage=f.baseline)
            f.cov += f.gains[min(f.n - 1, len(f.gains) - 1)]
            return EvalResult(ok=f.eval_ok, coverage=f.cov)

        @activity.defn(name="run_agent")
        async def agent(spec) -> AgentResult:
            f.n += 1
            f.running += 1
            f.peak = max(f.peak, f.running)
            await asyncio.sleep(0.01)
            f.running -= 1
            f.calls.append(("agent", f.n))
            return AgentResult(run_id=f"r{f.n}", outcome=f.outcomes.get(f.n, "pushed"), branch=f"ai/coverage-r{f.n}", cost_usd=f.cost)

        @activity.defn(name="record_agent_run")
        async def rec(repo, iteration, r, accepted) -> None:
            f.calls.append(("record", iteration, accepted))

        @activity.defn(name="record_issues")
        async def issues(repo, run_id) -> int:
            return 0

        @activity.defn(name="post_summary")
        async def summ(repo, text) -> None:
            f.calls.append(("summary", text))

        return [ev, agent, rec, issues, summ]


async def run_repo(fakes, inp, signals=None):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=Q, workflows=[ImproveRepoWorkflow], activities=fakes.activities()):
            h = await env.client.start_workflow(ImproveRepoWorkflow.run, inp, id=f"t-{uuid.uuid4()}", task_queue=Q)
            if signals:
                await signals(h, env)
            return await h.result()


async def test_stops_when_target_reached():
    f = Fakes(baseline=10, gains=(30, 30, 30))
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=60))
    assert r.stop_reason == "target-reached" and r.final_coverage == 70 and len(r.iterations) == 2
    assert [c for c in f.calls if c[0] == "agent"] == [("agent", 1), ("agent", 2)]


async def test_stalls_after_k_iterations_without_gain():
    f = Fakes(baseline=10, gains=(0.2, 0.2, 0.2, 0.2))
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=90, max_no_improve=2))
    assert r.stop_reason == "stalled" and len(r.iterations) == 2 and r.final_coverage == 10      # the unaccepted gains do not count


async def test_budget_stops_before_overspending():
    f = Fakes(baseline=10, gains=(5, 5, 5, 5), cost=2.5)
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=90, budget_usd=6.0, per_run_budget_usd=2.5, max_iterations=10))
    assert r.stop_reason == "budget-exhausted" and r.total_cost_usd <= 6.0 and len(r.iterations) == 2


async def test_failed_agent_runs_count_as_no_improvement():
    f = Fakes(outcomes={1: "integrity-failed", 2: "no-changes"})
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=90, max_no_improve=2))
    assert r.stop_reason == "stalled" and [i.outcome for i in r.iterations] == ["integrity-failed", "no-changes"]
    assert not any(c[0] == "eval" and c[1] != "main" for c in f.calls)                          # nothing pushed, nothing evaluated


async def test_failed_evaluation_gates_the_iteration():
    f = Fakes(gains=(40,), eval_ok=False)
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=90, max_no_improve=1))
    assert r.final_coverage == 10 and r.iterations[0].accepted is False


async def test_waits_for_human_approval_then_continues():
    f = Fakes(gains=(60,))

    async def approve(h, env):
        for _ in range(100):
            if (await h.query(ImproveRepoWorkflow.status))["status"].endswith("awaiting-approval"):
                break
            await asyncio.sleep(0.05)
        await h.signal(ImproveRepoWorkflow.human_approval, {"pr": 1})

    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=60, require_approval=True), approve)
    assert r.stop_reason == "target-reached" and r.iterations[0].accepted


async def test_approval_timeout_stops_the_loop():
    f = Fakes(gains=(60,))
    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=90, require_approval=True, approval_timeout_hours=1))
    assert r.stop_reason == "approval-timeout"


async def test_pause_blocks_new_iterations_until_resume():
    f = Fakes(gains=(60,))

    async def pause_resume(h, env):
        await h.signal(ImproveRepoWorkflow.pause)
        await asyncio.sleep(0.5)
        assert (await h.query(ImproveRepoWorkflow.status))["paused"] is True
        await h.signal(ImproveRepoWorkflow.resume)

    r = await run_repo(f, RepoInput(repo="capstone/a", target_coverage=60), pause_resume)
    assert r.stop_reason == "target-reached"


async def test_fleet_fan_out_is_bounded_and_respects_the_fleet_budget():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=Q, workflows=[ImproveFleetWorkflow, StubRepo]):
            res: FleetSummary = await env.client.execute_workflow(
                ImproveFleetWorkflow.run, FleetInput(repos=[f"capstone/r{i}" for i in range(6)], max_parallel=2, fleet_budget_usd=4.0), id=f"f-{uuid.uuid4()}", task_queue=Q)
    # two at a time at $1.50 each: after 2 rounds ($6.00 >= $4.00) the remaining repos are skipped
    assert res.stop_reason == "fleet-budget" and res.by_repo["capstone/r5"] == "skipped-fleet-budget"
    assert sum(1 for v in res.by_repo.values() if v == "target-reached") in (4,)
