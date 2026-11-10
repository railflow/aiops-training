"""The worker: YOUR process. It polls a task queue and runs workflow and activity code. Run 2+ of them; any can pick up any task.

Settings come from the environment so the same image runs on a laptop, in kind and in production:
  TEMPORAL_ADDRESS    frontend host:port            (default localhost:7233)
  TEMPORAL_NAMESPACE  Temporal namespace            (default "default")
  TASK_QUEUE          queue to poll                 (default enterprise-batch-queue)
  TEMPORAL_API_KEY    only for Temporal Cloud       (never print it, never commit it)
  METRICS_ADDRESS     Prometheus /metrics bind addr (default 0.0.0.0:9000), also used as the Kubernetes probe target
"""
import asyncio
import logging
import os
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import Worker

from activities import ALL_ACTIVITIES
from workflow import MonthlyKickoffWorkflow, MonthlyTaxProcessingWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    runtime = Runtime(telemetry=TelemetryConfig(metrics=PrometheusConfig(bind_address=os.environ.get("METRICS_ADDRESS", "0.0.0.0:9000"))))
    api_key = os.environ.get("TEMPORAL_API_KEY")
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
        runtime=runtime,
        api_key=api_key or None,
        tls=bool(api_key),  # Temporal Cloud needs TLS; for self-hosted TLS/mTLS see the SDK docs (check the docs)
    )
    queue = os.environ.get("TASK_QUEUE", "enterprise-batch-queue")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows event loops do not support add_signal_handler; Ctrl+C still raises KeyboardInterrupt
            pass
    async with Worker(
        client,
        task_queue=queue,
        workflows=[MonthlyTaxProcessingWorkflow, MonthlyKickoffWorkflow],
        activities=ALL_ACTIVITIES,
        graceful_shutdown_timeout=timedelta(seconds=20),  # on SIGTERM, give running activities a moment before they are handed back
    ):
        logging.info("worker polling task queue %r in namespace %r", queue, client.namespace)
        await stop.wait()
    logging.info("worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
