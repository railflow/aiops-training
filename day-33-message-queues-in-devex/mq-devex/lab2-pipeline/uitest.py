#!/usr/bin/env python3
"""UI-test stage. Listens for ci.build.completed, pretends to run UI tests, announces ci.test.uitest.completed.
UITEST_SECONDS (default 0.2) is how long the fake tests take: set it to 20 and kill the process mid-test to watch redelivery (lab step 5)."""
import asyncio
import os

import devbus

NAME = "uitest"


async def handle(ev, ctx):
    d = ev["data"]
    if "repo" not in d or "sha" not in d:
        raise devbus.PermanentError("ci.build.completed needs repo and sha")
    await asyncio.sleep(float(os.environ.get("UITEST_SECONDS", "0.2")))
    passed = not d.get("flags", {}).get("fail_ui", False)
    out = devbus.new_event("ci.test.uitest.completed", {"repo": d["repo"], "sha": d["sha"], "passed": passed, "tests": 42, "failed": 0 if passed else 3},
                           source=f"worker/{NAME}", parent=ev, event_id=devbus.derived_id(ev["id"], "uitest"))
    return [("ci.test.uitest.completed", out)]


if __name__ == "__main__":
    devbus.main(NAME, "ci.build.completed", handle, ack_wait=float(os.environ.get("ACK_WAIT", "10")))
