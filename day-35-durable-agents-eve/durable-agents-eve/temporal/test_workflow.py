"""Workflow tests with Temporal's time-skipping test server: the approval wait is a durable timer, so a four-hour wait costs nothing."""
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import lab_common as lab
from agent_workflow import TASK_QUEUE, CoverageAgent, decide_activity, tool_activity


@pytest.fixture(autouse=True)
def lab_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_DIR", str(tmp_path))
    for k in ("LAB_DIE_AT", "LAB_NO_IDEMPOTENCY", "LAB_STEP_MS"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


async def run_workflow(env, repo, after=None):
    with ThreadPoolExecutor() as pool:
        async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[CoverageAgent], activities=[decide_activity, tool_activity], activity_executor=pool):
            handle = await env.client.start_workflow(CoverageAgent.run, f"Improve coverage. repo={repo}", id=f"t-{uuid.uuid4()}", task_queue=TASK_QUEUE)
            if after:
                await after(handle)
            return await handle.result()


async def wait_for_approval(handle):
    import asyncio
    for _ in range(200):
        if (await handle.query(CoverageAgent.state))["waiting_for_approval"]:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("never reached the approval wait")


async def test_approved_run_opens_one_pull_request():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async def approve(h):
            await wait_for_approval(h)
            await h.signal(CoverageAgent.approve, "approve")
        assert (await run_workflow(env, "a-1", approve)).startswith("finished a-1")
    assert len(lab.pull_requests()) == 1


async def test_denied_run_opens_none():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async def deny(h):
            await wait_for_approval(h)
            await h.signal(CoverageAgent.approve, "deny")
        assert await run_workflow(env, "a-1", deny) == "stopped: pull request not approved"
    assert lab.pull_requests() == []


async def test_unanswered_approval_times_out_after_four_hours_of_skipped_time():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        assert await run_workflow(env, "a-1") == "stopped: approval timed out"
    assert lab.pull_requests() == []


def test_the_scripted_model_repeats_an_interrupted_call():
    d = lab.decide("repo=a-1", [("run_tests", False), ("write_test_file", True)])
    assert d["tool"] == "write_test_file"


def test_open_pr_is_idempotent_and_the_naive_version_is_not(monkeypatch):
    lab.open_pr("a-1")
    lab.open_pr("a-1")
    assert len(lab.pull_requests()) == 1
    monkeypatch.setenv("LAB_NO_IDEMPOTENCY", "1")
    lab.open_pr("a-1")
    assert len(lab.pull_requests()) == 2
