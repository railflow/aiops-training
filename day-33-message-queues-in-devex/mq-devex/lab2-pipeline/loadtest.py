#!/usr/bin/env python3
"""Load-test stage (Python stand-in; loadtest_consumer.go.txt shows the same consumer in Go). Runs in parallel with uitest: nobody told either of them about the other."""
import asyncio
import os

import devbus

NAME = "loadtest"
P95_LIMIT_MS = 300


async def handle(ev, ctx):
    d = ev["data"]
    await asyncio.sleep(float(os.environ.get("LOADTEST_SECONDS", "0.3")))
    p95 = 480 if d.get("flags", {}).get("slow_load") else 180
    out = devbus.new_event("ci.test.loadtest.completed", {"repo": d["repo"], "sha": d["sha"], "p95_ms": p95, "passed": p95 <= P95_LIMIT_MS},
                           source=f"worker/{NAME}", parent=ev, event_id=devbus.derived_id(ev["id"], "loadtest"))
    return [("ci.test.loadtest.completed", out)]


if __name__ == "__main__":
    devbus.main(NAME, "ci.build.completed", handle, ack_wait=float(os.environ.get("ACK_WAIT", "10")))
