#!/usr/bin/env python3
"""The strangler facade. Callers publish ci.requested and never care which implementation runs it. The facade reads a flag from a
JetStream key-value bucket on EVERY request, so you change the rollout with one command and no redeploy:

  nats kv put flags ci-runner legacy        everything goes to the old system (the default if the key is missing)
  nats kv put flags ci-runner shadow        old system is the answer of record; the new one ALSO runs, marked shadow, and results are compared
  nats kv put flags ci-runner canary:20     20% of repos (stable per repo name) go to the new implementation
  nats kv put flags ci-runner new           everything goes to the new implementation; delete the legacy adapter when you trust it

Fowler's Strangler Fig, in one file: the new thing grows around the old one behind a seam, takes over piece by piece, and the old one is removed last.
"""
import hashlib

from nats.js.api import KeyValueConfig

import devbus

NAME = "ci-facade"
BUCKET = "flags"
KEY = "ci-runner"


async def get_flag(js) -> str:
    try:
        kv = await js.key_value(BUCKET)
    except Exception:
        kv = await js.create_key_value(config=KeyValueConfig(bucket=BUCKET))
    try:
        return (await kv.get(KEY)).value.decode().strip()
    except Exception:
        return "legacy"


def pick(flag: str, repo: str) -> list:
    """Pure function: which implementations run, and is each one a shadow? -> [(impl, shadow)]"""
    if flag == "legacy":
        return [("legacy", False)]
    if flag == "new":
        return [("new", False)]
    if flag == "shadow":
        return [("legacy", False), ("new", True)]
    if flag.startswith("canary:"):
        pct = int(flag.split(":", 1)[1])
        bucket = int(hashlib.sha256(repo.encode()).hexdigest(), 16) % 100
        return [("new", False)] if bucket < pct else [("legacy", False)]
    raise devbus.PermanentError(f"unknown flag value {flag!r}")


async def handle(ev, ctx):
    d = ev["data"]
    if "repo" not in d or "sha" not in d:
        raise devbus.PermanentError("ci.requested needs repo and sha")
    flag = await get_flag(ctx.js)
    out = []
    for impl, shadow in pick(flag, d["repo"]):
        run = devbus.new_event(f"ci.run.{impl}", {**d, "impl": impl, "shadow": shadow, "flag": flag}, source=f"worker/{NAME}", parent=ev,
                               event_id=devbus.derived_id(ev["id"], f"run-{impl}"))
        out.append((f"ci.run.{impl}", run))
    return out


if __name__ == "__main__":
    devbus.main(NAME, "ci.requested", handle)
