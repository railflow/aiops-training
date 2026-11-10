#!/usr/bin/env python3
"""Pretend to be the build job: publish ci.build.completed. Everything downstream reacts; this script knows nobody.

  python3 emit_build.py --repo orders-api --sha 4f2a9c1                 # a healthy build
  python3 emit_build.py --repo orders-api --sha 4f2a9c1 --fail-ui       # the UI tests will fail
  python3 emit_build.py --repo orders-api --sha 4f2a9c1 --slow-load     # load test p95 over its limit
Prints the correlation id: grep for it in every worker's log, or query ClickHouse for it (sql/queries.sql).
"""
import argparse
import asyncio
import uuid

import devbus


async def emit(js, repo: str, sha: str, fail_ui: bool = False, slow_load: bool = False, corr: str = "") -> dict:
    ev = devbus.new_event("ci.build.completed", {"repo": repo, "sha": sha, "artifact": f"registry.local/{repo}:{sha}",
                                                   "flags": {"fail_ui": fail_ui, "slow_load": slow_load}},
                          source=f"build/{repo}", subject=f"{repo}@{sha}")
    ev["correlationid"] = corr or ev["correlationid"]
    await devbus.publish(js, "ci.build.completed", ev)
    return ev


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sha", default=uuid.uuid4().hex[:7])
    ap.add_argument("--fail-ui", action="store_true")
    ap.add_argument("--slow-load", action="store_true")
    a = ap.parse_args()
    nc, js = await devbus.connect()
    await devbus.ensure_stream(js)
    ev = await emit(js, a.repo, a.sha, a.fail_ui, a.slow_load)
    print(f"published ci.build.completed  correlationid={ev['correlationid']}")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
