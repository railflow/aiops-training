"""Capstone workflows. Deterministic: no clocks, randomness or I/O here (see Day 27). Every side effect is an activity.

  ImproveRepoWorkflow   baseline -> loop(agent, evaluate, record, decide) -> summary.  Signals: pause, resume, human_approval, ci_finished. Query: status.
  ImproveFleetWorkflow  fan out one ImproveRepoWorkflow per repo with bounded concurrency, a fleet budget, pause/resume.
  MeasureRepoWorkflow   one measurement of main (started by the webhook on push to main).
  FixIssueWorkflow      one fix-issue agent run for an issue labelled ai-fix, then wait for a human.
"""
import asyncio
from datetime import timedelta
from typing import List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from flow_models import (AgentResult, AgentSpec, EvalResult, EvalSpec, FleetInput, FleetSummary, IterationRecord, RepoInput, RepoSummary)

SHORT = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10), backoff_coefficient=2.0)
ONCE = RetryPolicy(maximum_attempts=1)            # the agent spends money and pushes: never auto-retry it


def short(repo: str) -> str:
    return repo.replace("/", "-").lower()


@workflow.defn
class ImproveRepoWorkflow:
    def __init__(self) -> None:
        self._paused = False
        self._approvals: List[dict] = []
        self._ci: List[dict] = []
        self._status = "starting"
        self._coverage: Optional[float] = None
        self._spent = 0.0

    @workflow.signal
    def pause(self) -> None:
        self._paused = True

    @workflow.signal
    def resume(self) -> None:
        self._paused = False

    @workflow.signal
    def human_approval(self, payload: dict) -> None:
        self._approvals.append(payload)

    @workflow.signal
    def ci_finished(self, payload: dict) -> None:
        self._ci.append(payload)

    @workflow.query
    def status(self) -> dict:
        return {"status": self._status, "coverage": self._coverage, "spent_usd": round(self._spent, 2), "paused": self._paused}

    async def _eval(self, spec: EvalSpec) -> EvalResult:
        return await workflow.execute_activity("measure_or_evaluate", spec, result_type=EvalResult, start_to_close_timeout=timedelta(minutes=45),
                                               heartbeat_timeout=timedelta(minutes=2), retry_policy=SHORT)

    @workflow.run
    async def run(self, inp: RepoInput) -> RepoSummary:
        tag = short(inp.repo)[:24]
        self._status = "measuring-baseline"
        base = await self._eval(EvalSpec(repo=inp.repo, run_id=f"{tag}-base-{workflow.uuid4().hex[:8]}", iteration=0))
        baseline = base.coverage
        self._coverage = baseline
        records: List[IterationRecord] = []
        no_improve = 0
        stop = "max-iterations"

        for i in range(1, inp.max_iterations + 1):
            await workflow.wait_condition(lambda: not self._paused)          # pause/resume: durable, survives restarts
            if self._coverage is not None and self._coverage >= inp.target_coverage:
                stop = "target-reached"
                break
            if self._spent + inp.per_run_budget_usd > inp.budget_usd:
                stop = "budget-exhausted"
                break
            self._status = f"iteration-{i}-agent"
            run_id = f"{tag}-i{i}-{workflow.uuid4().hex[:8]}"
            agent: AgentResult = await workflow.execute_activity(
                "run_agent", AgentSpec(repo=inp.repo, run_id=run_id, iteration=i, target_coverage=inp.target_coverage, focus=inp.focus, max_budget_usd=inp.per_run_budget_usd, model=inp.model),
                result_type=AgentResult, start_to_close_timeout=timedelta(minutes=40), heartbeat_timeout=timedelta(minutes=2), retry_policy=ONCE)
            self._spent += agent.cost_usd
            accepted, gain, cov = False, 0.0, self._coverage
            if agent.outcome == "pushed":
                self._status = f"iteration-{i}-evaluating"
                ev = await self._eval(EvalSpec(repo=inp.repo, run_id=f"{run_id}-ev", branch=agent.branch, iteration=i, agent_run_id=run_id, prev_coverage=self._coverage))
                cov = ev.coverage if ev.coverage is not None else self._coverage
                gain = (cov or 0.0) - (self._coverage or 0.0)
                if ev.ok and gain >= inp.min_gain:
                    if inp.require_approval:
                        self._status = f"iteration-{i}-awaiting-approval"
                        got = await _wait_for(lambda: len(self._approvals) > 0, timedelta(hours=inp.approval_timeout_hours))
                        if not got:
                            records.append(IterationRecord(i, "approval-timeout", cov, gain, agent.cost_usd, agent.branch, agent.pr_url, False))
                            await workflow.execute_activity("record_agent_run", args=[inp.repo, i, agent, False], start_to_close_timeout=timedelta(minutes=2), retry_policy=SHORT)
                            stop = "approval-timeout"
                            break
                        self._approvals.clear()
                    accepted = True
                    self._coverage = cov
                    no_improve = 0
                else:
                    no_improve += 1
            else:
                no_improve += 1
            await workflow.execute_activity("record_agent_run", args=[inp.repo, i, agent, accepted], start_to_close_timeout=timedelta(minutes=2), retry_policy=SHORT)
            await workflow.execute_activity("record_issues", args=[inp.repo, run_id], start_to_close_timeout=timedelta(minutes=5), retry_policy=SHORT)
            records.append(IterationRecord(i, agent.outcome, cov, gain, agent.cost_usd, agent.branch, agent.pr_url, accepted))
            if no_improve >= inp.max_no_improve:
                stop = "stalled"
                break
        else:
            if self._coverage is not None and self._coverage >= inp.target_coverage:
                stop = "target-reached"

        self._status = "summarising"
        summary = RepoSummary(inp.repo, stop, baseline, self._coverage, round(self._spent, 4), records)
        text = (f"Stop reason: **{stop}**. Coverage {baseline} -> {self._coverage}. Spend ${self._spent:.2f} over {len(records)} iterations.\n\n"
                + "\n".join(f"- iteration {r.iteration}: {r.outcome}, coverage {r.coverage}, gain {r.gain:+.1f}, accepted={r.accepted} {r.pr_url}" for r in records))
        await workflow.execute_activity("post_summary", args=[inp.repo, text], start_to_close_timeout=timedelta(minutes=2), retry_policy=SHORT)
        self._status = "done"
        return summary


async def _wait_for(cond, timeout: timedelta) -> bool:
    try:
        await workflow.wait_condition(cond, timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


@workflow.defn
class ImproveFleetWorkflow:
    def __init__(self) -> None:
        self._paused = False
        self._running: dict = {}
        self._cost = 0.0
        self._done = 0

    @workflow.signal
    async def pause(self) -> None:
        self._paused = True
        for h in list(self._running.values()):
            await h.signal("pause")

    @workflow.signal
    async def resume(self) -> None:
        self._paused = False
        for h in list(self._running.values()):
            await h.signal("resume")

    @workflow.query
    def progress(self) -> dict:
        return {"running": sorted(self._running), "completed": self._done, "spent_usd": round(self._cost, 2), "paused": self._paused}

    @workflow.run
    async def run(self, inp: FleetInput) -> FleetSummary:
        sem = asyncio.Semaphore(inp.max_parallel)
        results: dict = {}
        failed = 0
        stop = "all-done"

        async def one(repo: str):
            nonlocal failed, stop
            async with sem:
                await workflow.wait_condition(lambda: not self._paused)
                if self._cost >= inp.fleet_budget_usd:
                    results[repo] = "skipped-fleet-budget"
                    stop = "fleet-budget"
                    return
                per = RepoInput(**{**inp.per_repo.__dict__, "repo": repo})
                handle = await workflow.start_child_workflow("ImproveRepoWorkflow", per, id=f"improve-{short(repo)}", result_type=RepoSummary)
                self._running[repo] = handle
                try:
                    summary: RepoSummary = await handle
                    self._cost += summary.total_cost_usd
                    results[repo] = summary.stop_reason
                except Exception:
                    failed += 1
                    results[repo] = "failed"
                finally:
                    self._running.pop(repo, None)
                    self._done += 1

        await asyncio.gather(*(one(r) for r in inp.repos))
        return FleetSummary(started=len(inp.repos), completed=self._done, failed=failed, total_cost_usd=round(self._cost, 4), stop_reason=stop, by_repo=results)


@workflow.defn
class MeasureRepoWorkflow:
    @workflow.run
    async def run(self, args: dict) -> dict:
        ev: EvalResult = await workflow.execute_activity(
            "measure_or_evaluate", EvalSpec(repo=args["repo"], run_id=f"{short(args['repo'])[:24]}-m-{workflow.uuid4().hex[:8]}", iteration=0), result_type=EvalResult,
            start_to_close_timeout=timedelta(minutes=45), heartbeat_timeout=timedelta(minutes=2), retry_policy=SHORT)
        return {"repo": args["repo"], "coverage": ev.coverage, "ok": ev.ok}


@workflow.defn
class FixIssueWorkflow:
    def __init__(self) -> None:
        self._approved = False

    @workflow.signal
    def human_approval(self, payload: dict) -> None:
        self._approved = True

    @workflow.run
    async def run(self, args: dict) -> dict:
        repo, issue = args["repo"], int(args["issue_number"])
        run_id = f"{short(repo)[:24]}-fix{issue}-{workflow.uuid4().hex[:8]}"
        agent: AgentResult = await workflow.execute_activity(
            "run_agent", AgentSpec(repo=repo, run_id=run_id, iteration=1, task="fix-issue", issue_number=issue), result_type=AgentResult,
            start_to_close_timeout=timedelta(minutes=40), heartbeat_timeout=timedelta(minutes=2), retry_policy=ONCE)
        ev = EvalResult(ok=False)
        if agent.outcome == "pushed":
            ev = await workflow.execute_activity("measure_or_evaluate", EvalSpec(repo=repo, run_id=f"{run_id}-ev", branch=agent.branch, iteration=1, agent_run_id=run_id, allow_src_changes=True),
                                                 result_type=EvalResult, start_to_close_timeout=timedelta(minutes=45), heartbeat_timeout=timedelta(minutes=2), retry_policy=SHORT)
        await workflow.execute_activity("record_agent_run", args=[repo, 1, agent, ev.ok], start_to_close_timeout=timedelta(minutes=2), retry_policy=SHORT)
        return {"repo": repo, "issue": issue, "outcome": agent.outcome, "evaluation_ok": ev.ok, "pr_url": agent.pr_url}
