"""Activities: the code that touches the outside world. Anything that can fail, take a long time, or have a side effect goes here.

Activities may use the clock, random numbers, files, HTTP and databases. Workflow code (workflow.py) may not.
Behaviour for the demos is switched with environment variables so you can break things on purpose without editing code:
  PDF_COUNT (default 20), PDF_SECONDS_EACH (default 0.5)   how big and slow the PDF job is
  IRS_FAIL_TIMES (default 0)                               the "IRS API" fails this many attempts, then works
"""
import asyncio
import os
import re
import socket

from temporalio import activity
from temporalio.exceptions import ApplicationError

BATCH_ID = re.compile(r"^BATCH-\d{4}-\d{2}$")


def _host() -> str:
    # Inside Kubernetes the hostname is the worker pod name, which makes "who ran this?" visible. WORKER_NAME overrides it on a laptop.
    return os.environ.get("WORKER_NAME") or socket.gethostname()


@activity.defn
async def verify_records(batch_id: str) -> int:
    activity.logger.info("verifying records for %s on %s", batch_id, _host())
    if not BATCH_ID.match(batch_id):
        # A bug in the input will not fix itself on attempt 2, so mark it non-retryable: the workflow fails fast.
        raise ApplicationError(f"invalid batch id {batch_id!r}", type="InvalidTaxData", non_retryable=True)
    await asyncio.sleep(0.2)
    return 1250


@activity.defn
async def generate_pdfs(batch_id: str) -> int:
    """Long-running and resumable: report progress with a heartbeat, and resume from the last heartbeat after a retry."""
    count = int(os.environ.get("PDF_COUNT", "20"))
    each = float(os.environ.get("PDF_SECONDS_EACH", "0.5"))
    start = 0
    details = activity.info().heartbeat_details
    if details:
        start = int(details[0])
        activity.logger.info("resuming at pdf %d after a retry", start)
    for i in range(start, count):
        await asyncio.sleep(each)
        activity.heartbeat(i + 1)  # tells the server "still alive, and this is how far I got"
        activity.logger.info("pdf %d/%d for %s on %s", i + 1, count, batch_id, _host())
    return count


@activity.defn
async def check_irs(batch_id: str) -> str:
    """Stand-in for an external API that can be down. The attempt number comes from Temporal, so there is no retry state in our code."""
    attempt = activity.info().attempt
    fail_times = int(os.environ.get("IRS_FAIL_TIMES", "0"))
    activity.logger.info("calling IRS for %s, attempt %d", batch_id, attempt)
    if attempt <= fail_times:
        raise ConnectionError(f"IRS API unavailable (simulated, attempt {attempt} of {fail_times} failures)")
    return f"IRS-{batch_id}-OK"


@activity.defn
async def notify_reviewers(batch_id: str) -> None:
    activity.logger.info("approval requested for %s (send a real message here)", batch_id)


@activity.defn
async def finalize_batch(batch_id: str, approver: str) -> str:
    activity.logger.info("finalizing %s approved by %s", batch_id, approver)
    return "finalized"


@activity.defn
async def delete_generated_pdfs(batch_id: str) -> None:
    activity.logger.info("compensation: deleting generated PDFs for %s", batch_id)


@activity.defn
async def notify_failure(batch_id: str, reason: str) -> None:
    activity.logger.info("compensation: telling the team %s failed: %s", batch_id, reason)


ALL_ACTIVITIES = [
    verify_records, generate_pdfs, check_irs, notify_reviewers, finalize_batch, delete_generated_pdfs, notify_failure,
]
