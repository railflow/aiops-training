"""Workflow tests with the time-skipping test server: a 72-hour approval window runs in milliseconds.

The first run downloads the Temporal test-server binary (the SDK does this for you; it needs network access once, then it is cached).
Activities are replaced with fakes that have the same names, so these tests check orchestration, not the activities themselves.
"""
import uuid
from datetime import timedelta

import pytest
from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from models import BatchInput
from workflow import MonthlyKickoffWorkflow, MonthlyTaxProcessingWorkflow

QUEUE = "test-queue"


@workflow.defn(name="MonthlyTaxProcessingWorkflow")
class StubBatch:
    """Same name as the real workflow, trivial body: lets the kickoff test run without the activities."""

    @workflow.run
    async def run(self, inp: BatchInput) -> str:
        return inp.batch_id


class Fakes:
    def __init__(self, irs_failures: int = 0, bad_batch: bool = False):
        self.calls: list[str] = []
        self.irs_attempts = 0
        self.irs_failures = irs_failures
        self.bad_batch = bad_batch

    def activities(self):
        @activity.defn(name="verify_records")
        async def verify_records(batch_id: str) -> int:
            self.calls.append("verify_records")
            if self.bad_batch:
                raise ApplicationError("invalid", type="InvalidTaxData", non_retryable=True)
            return 10

        @activity.defn(name="generate_pdfs")
        async def generate_pdfs(batch_id: str) -> int:
            self.calls.append("generate_pdfs")
            return 10

        @activity.defn(name="check_irs")
        async def check_irs(batch_id: str) -> str:
            self.calls.append("check_irs")
            self.irs_attempts += 1
            if self.irs_attempts <= self.irs_failures:
                raise ConnectionError("IRS down")
            return "IRS-OK"

        @activity.defn(name="notify_reviewers")
        async def notify_reviewers(batch_id: str) -> None:
            self.calls.append("notify_reviewers")

        @activity.defn(name="finalize_batch")
        async def finalize_batch(batch_id: str, approver: str) -> str:
            self.calls.append("finalize_batch")
            return "finalized"

        @activity.defn(name="delete_generated_pdfs")
        async def delete_generated_pdfs(batch_id: str) -> None:
            self.calls.append("delete_generated_pdfs")

        @activity.defn(name="notify_failure")
        async def notify_failure(batch_id: str, reason: str) -> None:
            self.calls.append("notify_failure")

        return [verify_records, generate_pdfs, check_irs, notify_reviewers, finalize_batch, delete_generated_pdfs, notify_failure]


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as e:
        yield e


async def run_workflow(env, fakes, *, signal=None, batch="BATCH-2026-11"):
    async with Worker(env.client, task_queue=QUEUE, workflows=[MonthlyTaxProcessingWorkflow], activities=fakes.activities()):
        handle = await env.client.start_workflow(
            MonthlyTaxProcessingWorkflow.run,
            BatchInput(batch),
            id=f"test-{uuid.uuid4()}",
            task_queue=QUEUE,
        )
        if signal:
            await handle.signal(signal[0], signal[1])
        return handle, await handle.result()


async def test_happy_path_with_approval(env):
    fakes = Fakes()
    _, result = await run_workflow(env, fakes, signal=("approve", "alice"))
    assert result.status == "finalized" and result.approved_by == "alice" and result.pdfs == 10
    assert fakes.calls == ["verify_records", "generate_pdfs", "check_irs", "notify_reviewers", "finalize_batch"]


async def test_irs_outage_is_retried_without_any_retry_code(env):
    fakes = Fakes(irs_failures=3)
    _, result = await run_workflow(env, fakes, signal=("approve", "bob"))
    assert result.status == "finalized"
    assert fakes.irs_attempts == 4  # 3 failures + 1 success, with backoff time skipped by the test server
    assert fakes.calls.count("generate_pdfs") == 1  # earlier steps were NOT redone


async def test_no_approval_times_out_and_compensates(env):
    fakes = Fakes()
    with pytest.raises(WorkflowFailureError) as err:
        await run_workflow(env, fakes)  # nobody approves: 72 simulated hours pass
    assert "no approval within 72h" in str(err.value.cause)
    assert fakes.calls[-2:] == ["delete_generated_pdfs", "notify_failure"]


async def test_rejection_compensates(env):
    fakes = Fakes()
    with pytest.raises(WorkflowFailureError) as err:
        await run_workflow(env, fakes, signal=("reject", "numbers do not add up"))
    assert "rejected: numbers do not add up" in str(err.value.cause)
    assert fakes.calls[-2:] == ["delete_generated_pdfs", "notify_failure"]


async def test_bad_input_fails_fast_without_retries_or_pdf_cleanup(env):
    fakes = Fakes(bad_batch=True)
    with pytest.raises(WorkflowFailureError):
        await run_workflow(env, fakes, batch="not-a-batch")
    assert fakes.calls == ["verify_records", "notify_failure"]  # one attempt only; no PDFs existed, so nothing to delete


async def test_stage_query(env):
    fakes = Fakes()
    async with Worker(env.client, task_queue=QUEUE, workflows=[MonthlyTaxProcessingWorkflow], activities=fakes.activities()):
        handle = await env.client.start_workflow(
            MonthlyTaxProcessingWorkflow.run, BatchInput("BATCH-2026-11", cooling_off_seconds=3600),
            id=f"test-{uuid.uuid4()}", task_queue=QUEUE,
        )
        await env.sleep(timedelta(minutes=30))  # skip half the cooling-off timer
        assert (await handle.query(MonthlyTaxProcessingWorkflow.stage)).startswith("cooling off")
        await handle.signal("approve", "carol")
        assert (await handle.result()).approved_by == "carol"


async def test_kickoff_derives_the_batch_id_from_workflow_time_and_starts_a_child(env):
    async with Worker(env.client, task_queue=QUEUE, workflows=[StubBatch, MonthlyKickoffWorkflow]):
        batch_id = await env.client.execute_workflow(MonthlyKickoffWorkflow.run, 60, id=f"kick-{uuid.uuid4()}", task_queue=QUEUE)
        assert batch_id.startswith("BATCH-20") and len(batch_id) == len("BATCH-2026-11")
        child = env.client.get_workflow_handle(f"monthly-tax-{batch_id}")
        assert await child.result() == batch_id


async def test_irs_down_for_six_hours_fails_the_workflow_and_compensates(env):
    fakes = Fakes(irs_failures=10_000)  # effectively "down all day"; the test server skips six hours of backoff in milliseconds
    with pytest.raises(WorkflowFailureError):
        await run_workflow(env, fakes)
    assert fakes.irs_attempts > 100
    assert fakes.calls[-2:] == ["delete_generated_pdfs", "notify_failure"]
