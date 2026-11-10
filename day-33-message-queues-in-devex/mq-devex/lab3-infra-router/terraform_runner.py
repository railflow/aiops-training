#!/usr/bin/env python3
"""The automation path. STAND-IN: it simulates "terraform plan, terraform apply" and invents outputs. It does not run Terraform.
To make it real, replace `fake_apply` with a Kubernetes Job (the capstone's JobRunner seam, Day 27) that runs terraform with a per-run workspace.
params.fail=true makes the apply fail so you can see the failure path. A failed apply is retried 2 times (a real one would also check for a stale lock)."""
import asyncio
import hashlib
import os

import devbus

NAME = "terraform-runner"


def fake_apply(req: dict) -> dict:
    if str(req.get("params", {}).get("fail", "")).lower() == "true":
        raise devbus.PermanentError("terraform apply failed: quota exceeded (simulated)")
    name, env = req["name"], req.get("env", "dev")
    h = hashlib.sha256(f"{name}{env}".encode()).hexdigest()[:8]
    return {"namespace": f"{name}-{env}", "database": f"{name}-{env}.{h}.eu-west-1.rds.example.internal", "secret": f"{name}-db"}


async def handle(ev, ctx):
    d = ev["data"]
    rid = d["request_id"]
    await asyncio.sleep(float(os.environ.get("TF_SECONDS", "0.2")))
    try:
        outputs = fake_apply(d["request"])
    except devbus.PermanentError as e:
        fail = devbus.new_event("infra.status", {"request_id": rid, "state": "failed", "reason": str(e)}, source=f"worker/{NAME}", parent=ev,
                                event_id=devbus.derived_id(ev["id"], "status-failed"))
        return [(f"infra.status.{rid}", fail)]
    done = devbus.new_event("infra.result", {"request_id": rid, "state": "done", "by": "automation", "outputs": outputs}, source=f"worker/{NAME}", parent=ev,
                            event_id=devbus.derived_id(ev["id"], "result"))
    return [(f"infra.result.{rid}", done)]


if __name__ == "__main__":
    devbus.main(NAME, "infra.work.terraform", handle)
