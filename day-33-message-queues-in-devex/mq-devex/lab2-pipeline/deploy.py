#!/usr/bin/env python3
"""Deploy stage: reacts to ci.gate.passed only. The stand-in "deploys" by emitting ci.deploy.completed (a real one would call Argo CD / Flux, Day 8)."""
import devbus

NAME = "deploy"


async def handle(ev, ctx):
    d = ev["data"]
    out = devbus.new_event("ci.deploy.completed", {"repo": d["repo"], "sha": d["sha"], "env": "staging"}, source=f"worker/{NAME}", parent=ev,
                           event_id=devbus.derived_id(ev["id"], "deploy"))
    return [("ci.deploy.completed", out)]


if __name__ == "__main__":
    devbus.main(NAME, "ci.gate.passed", handle)
