#!/usr/bin/env python3
"""Notifier: tells humans about the two outcomes that matter. It subscribes to ci.> and ignores the rest, which is how you add a new listener
without touching any other worker. NOTIFY_SINK is a file (stand-in for Slack/Jira); set NOTIFY_WEBHOOK to also POST JSON (not run in this repo's verification)."""
import json
import os
import urllib.request

import devbus

NAME = "notify"
INTERESTING = {"ci.gate.failed": "BLOCKED", "ci.deploy.completed": "DEPLOYED"}


async def handle(ev, ctx):
    label = INTERESTING.get(ev["type"])
    if not label:
        return []
    d = ev["data"]
    line = json.dumps({"label": label, "repo": d.get("repo"), "sha": d.get("sha"), "correlationid": ev["correlationid"], "at": devbus.now()})
    with open(os.environ.get("NOTIFY_SINK", os.path.join(ctx.state_dir, "notifications.jsonl")), "a") as f:
        f.write(line + "\n")
    url = os.environ.get("NOTIFY_WEBHOOK")
    if url:
        req = urllib.request.Request(url, data=json.dumps({"text": f"{label}: {d.get('repo')}@{d.get('sha')}"}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except OSError as e:
            raise devbus.Retry(f"webhook failed: {e}", delay=2)
    return []


if __name__ == "__main__":
    devbus.main(NAME, "ci.>", handle)
