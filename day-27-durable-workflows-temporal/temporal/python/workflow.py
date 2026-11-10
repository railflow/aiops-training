"""MonthlyTaxProcessingWorkflow: deterministic orchestration. Rules for this file:
  * no datetime.now(), random, uuid4, network, file or database calls: use workflow.now(), workflow.random(), workflow.uuid4() or an activity
  * no threads, no global mutable state, iterate dicts/sets in a stable order
  * time passes only through workflow.sleep / wait_condition / activity timeouts, all of which are durable
"""
import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

# Activities (and our own modules) are imported "passed through" so the sandbox does not re-import them on every replay.
with workflow.unsafe.imports_passed_through():
    from activities import (
        check_irs,
        delete_generated_pdfs,
        finalize_batch,
        generate_pdfs,
        notify_failure,
        notify_reviewers,
        verify_records,
    )
    from models import BatchInput, BatchResult


@workflow.defn
class MonthlyTaxProcessingWorkflow:
    def __init__(self) -> None:
        self._stage = "starting"
        self._approver: str | None = None
        self._rejection: str | None = None

    @workflow.signal
    def approve(self, approver: str) -> None:
        self._approver = approver

    @workflow.signal
    def reject(self, reason: str) -> None:
        self._rejection = reason

    @workflow.query
    def stage(self) -> str:
        return self._stage

    @workflow.run
    async def run(self, inp: BatchInput) -> BatchResult:
        pdfs_made = False
        try:
            # Step 1: verify DB records. A bad batch id is non-retryable (see activities.py), anything else retries by default.
            self._stage = "verifying records"
            await workflow.execute_activity(
                verify_records, inp.batch_id,
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 2: bulk PDFs. Long: heartbeat so a dead worker is noticed in 30s, not after the 2h limit. Max 5 attempts, first retry after 10s.
            self._stage = "generating PDFs"
            pdfs = await workflow.execute_activity(
                generate_pdfs, inp.batch_id,
                start_to_close_timeout=timedelta(hours=2),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=5),
                    maximum_attempts=5,
                ),
            )
            pdfs_made = True

            # Step 3: external API that can be down for hours. One try may take 1 minute; keep retrying (capped backoff) for up to 6 hours in total.
            self._stage = "checking IRS"
            irs_ref = await workflow.execute_activity(
                check_irs, inp.batch_id,
                start_to_close_timeout=timedelta(minutes=1),
                schedule_to_close_timeout=timedelta(hours=6),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=2),
                ),
            )

            # Step 4a: a durable timer. The worker may restart ten times during this day; the timer is stored on the server.
            self._stage = f"cooling off for {inp.cooling_off_seconds}s"
            await workflow.sleep(timedelta(seconds=inp.cooling_off_seconds))

            # Step 4b: wait for a human. A signal wakes us; a timeout ends the wait. Not a blind sleep: an approval at minute 5 is acted on at minute 5.
            self._stage = "waiting for approval"
            await workflow.execute_activity(
                notify_reviewers, inp.batch_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            try:
                await workflow.wait_condition(
                    lambda: self._approver is not None or self._rejection is not None,
                    timeout=timedelta(hours=inp.approval_timeout_hours),
                )
            except asyncio.TimeoutError:
                raise ApplicationError(
                    f"no approval within {inp.approval_timeout_hours}h", type="ApprovalTimeout", non_retryable=True
                )
            if self._rejection is not None:
                raise ApplicationError(f"rejected: {self._rejection}", type="Rejected", non_retryable=True)

            self._stage = "finalizing"
            status = await workflow.execute_activity(
                finalize_batch, args=[inp.batch_id, self._approver],
                start_to_close_timeout=timedelta(seconds=30),
            )
            self._stage = "done"
            return BatchResult(inp.batch_id, pdfs, irs_ref, self._approver, status)

        except (ActivityError, ApplicationError) as err:
            # Compensation (saga): undo what we did, tell people, then let the workflow fail so the failure is visible and queryable.
            self._stage = "compensating"
            if pdfs_made:
                await workflow.execute_activity(
                    delete_generated_pdfs, inp.batch_id, start_to_close_timeout=timedelta(minutes=1)
                )
            await workflow.execute_activity(
                notify_failure, args=[inp.batch_id, str(err.cause or err)], start_to_close_timeout=timedelta(minutes=1)
            )
            self._stage = "failed"
            raise


@workflow.defn
class MonthlyKickoffWorkflow:
    """Target of the Temporal Schedule. A schedule passes the SAME input every time, but the batch id must change every month,
    so this tiny parent derives it from workflow.now() (deterministic) and starts the real workflow as a child."""

    @workflow.run
    async def run(self, cooling_off_seconds: int = 86400) -> str:
        batch_id = workflow.now().strftime("BATCH-%Y-%m")
        await workflow.start_child_workflow(
            MonthlyTaxProcessingWorkflow.run,
            BatchInput(batch_id, cooling_off_seconds=cooling_off_seconds),
            id=f"monthly-tax-{batch_id}",
            parent_close_policy=workflow.ParentClosePolicy.ABANDON,  # the batch keeps running even if this parent finishes
        )
        return batch_id
