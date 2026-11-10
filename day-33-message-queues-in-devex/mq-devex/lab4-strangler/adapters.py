#!/usr/bin/env python3
"""Two adapters behind the facade. Both end by publishing the SAME event, ci.completed, with an `impl` field. That sameness is the whole point:
consumers of ci.completed cannot tell (and should not need to know) which implementation ran.

  python3 adapters.py legacy     wraps legacy/run_ci_legacy.sh (the anti-corruption layer: scrape the old output, emit a clean event)
  python3 adapters.py new        the replacement, written natively. NEW_BUG=1 makes it wrongly fail builds, so shadow mode has something to catch.
"""
import asyncio
import os
import sys
import time

import devbus

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.environ.get("LEGACY_SCRIPT", os.path.join(HERE, "legacy", "run_ci_legacy.sh"))


def parse_legacy(stdout: str, code: int) -> dict:
    kv = dict(line.split("=", 1) for line in stdout.splitlines() if "=" in line)
    return {"passed": kv.get("RESULT") == "SUCCESS" and code == 0, "tests": int(kv.get("TESTS", "0")), "url": kv.get("BUILD_URL", "")}


async def legacy_handle(ev, ctx):
    d = ev["data"]
    t0 = time.time()
    proc = await asyncio.create_subprocess_exec(SCRIPT, d["repo"], d["sha"], "fail" if d.get("flags", {}).get("fail") else "", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    res = parse_legacy(out.decode(), proc.returncode)
    return [("ci.completed", _completed(ev, res, "legacy", t0))]


async def new_handle(ev, ctx):
    d = ev["data"]
    t0 = time.time()
    await asyncio.sleep(float(os.environ.get("NEW_SECONDS", "0.1")))
    passed = not d.get("flags", {}).get("fail", False)
    if os.environ.get("NEW_BUG") == "1":
        passed = False
    return [("ci.completed", _completed(ev, {"passed": passed, "tests": 42, "url": f"http://new-ci.example.internal/{d['repo']}/{d['sha']}"}, "new", t0))]


def _completed(ev, res, impl, t0):
    d = ev["data"]
    return devbus.new_event("ci.completed", {"repo": d["repo"], "sha": d["sha"], "impl": impl, "shadow": d.get("shadow", False), "passed": res["passed"],
                                             "tests": res["tests"], "url": res["url"], "duration_ms": int((time.time() - t0) * 1000)},
                            source=f"worker/adapter-{impl}", parent=ev, event_id=devbus.derived_id(ev["id"], "completed"))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "legacy":
        devbus.main("adapter-legacy", "ci.run.legacy", legacy_handle)
    elif which == "new":
        devbus.main("adapter-new", "ci.run.new", new_handle)
    else:
        sys.exit("usage: adapters.py legacy|new")
