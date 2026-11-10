#!/usr/bin/env python3
"""Start and steer the capstone workflows from your laptop (needs `kubectl -n temporal port-forward svc/temporal-frontend 7233` or the dev server).

  python3 start.py fleet --csv ../work/repos.csv --limit 3 --parallel 2 --target 60 --fleet-budget 15
  python3 start.py repo capstone/notifications-py-001 --target 60
  python3 start.py pause   [improve-capstone-notifications-py-001 | capstone-fleet]
  python3 start.py resume  [id]
  python3 start.py status  [id]
  python3 start.py kill    [id]            # Temporal terminate. The Jobs already running are NOT stopped by this: also run
                                           #   kubectl -n capstone delete jobs -l app=agent --wait=false
"""
import argparse
import asyncio
import csv
import os
import sys

from temporalio.client import Client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_models import FleetInput, RepoInput  # noqa: E402
from flow_workflows import ImproveFleetWorkflow, ImproveRepoWorkflow  # noqa: E402

Q = os.environ.get("TASK_QUEUE", "capstone")


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fleet"); f.add_argument("--csv", required=True); f.add_argument("--org", default="capstone"); f.add_argument("--limit", type=int, default=3)
    f.add_argument("--parallel", type=int, default=2); f.add_argument("--target", type=float, default=60); f.add_argument("--fleet-budget", type=float, default=15)
    f.add_argument("--per-repo-budget", type=float, default=6); f.add_argument("--per-run-budget", type=float, default=2); f.add_argument("--approval", action="store_true")
    r = sub.add_parser("repo"); r.add_argument("repo"); r.add_argument("--target", type=float, default=60); r.add_argument("--approval", action="store_true")
    for name in ("pause", "resume", "status", "kill"):
        s = sub.add_parser(name); s.add_argument("id", nargs="?", default="capstone-fleet")
    a = ap.parse_args()
    c = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    if a.cmd == "fleet":
        names = [row["name"] for row in csv.DictReader(open(a.csv))][:a.limit]
        inp = FleetInput(repos=[f"{a.org}/{n}" for n in names], max_parallel=a.parallel, fleet_budget_usd=a.fleet_budget,
                         per_repo=RepoInput(repo="", target_coverage=a.target, budget_usd=a.per_repo_budget, per_run_budget_usd=a.per_run_budget, require_approval=a.approval))
        h = await c.start_workflow(ImproveFleetWorkflow.run, inp, id="capstone-fleet", task_queue=Q)
        print("started", h.id, h.result_run_id)
    elif a.cmd == "repo":
        h = await c.start_workflow(ImproveRepoWorkflow.run, RepoInput(repo=a.repo, target_coverage=a.target, require_approval=a.approval),
                                   id="improve-" + a.repo.replace("/", "-"), task_queue=Q)
        print("started", h.id, h.result_run_id)
    else:
        h = c.get_workflow_handle(a.id)
        if a.cmd in ("pause", "resume"):
            await h.signal(a.cmd)
            print(a.cmd, "sent to", a.id)
        elif a.cmd == "status":
            q = ImproveFleetWorkflow.progress if a.id == "capstone-fleet" else ImproveRepoWorkflow.status
            print(await h.query(q))
        else:
            await h.terminate(reason="kill switch")
            print("terminated", a.id)


if __name__ == "__main__":
    asyncio.run(main())
