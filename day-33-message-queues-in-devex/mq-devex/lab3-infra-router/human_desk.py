#!/usr/bin/env python3
"""The human path. Turns infra.human.<team> into a ticket and remembers it until a person acts through the CLI:
  platform request approve <id> --by alice     -> publishes infra.approval.<id>   (the desk then starts the automation named in the route's `then`)
  platform request complete <id> --by alice    -> publishes infra.completion.<id> (the human did the work by hand; result = done)
Tickets go to a JSONL file by default. With FORGEJO_URL, FORGEJO_TOKEN, FORGEJO_REPO set it ALSO opens an issue via the Forgejo API
(POST /api/v1/repos/{owner}/{repo}/issues; NOT run in this repo's verification: Forgejo was not available)."""
import json
import os
import sqlite3
import urllib.request

import devbus

NAME = "human-desk"


def _db(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    db = sqlite3.connect(os.path.join(state_dir, "tickets.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS tickets (rid TEXT PRIMARY KEY, team TEXT, request TEXT, then_runner TEXT, state TEXT)")
    return db


def open_forgejo_issue(rid, team, request, sla):
    url, token, repo = os.environ.get("FORGEJO_URL"), os.environ.get("FORGEJO_TOKEN"), os.environ.get("FORGEJO_REPO")
    if not (url and token and repo):
        return None
    body = {"title": f"[{team}] infra request {request.get('kind')} {request.get('name')}", "body": f"request id: `{rid}`\nSLA: {sla} min\n\n```json\n{json.dumps(request, indent=2)}\n```"}
    req = urllib.request.Request(f"{url.rstrip('/')}/api/v1/repos/{repo}/issues", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"token {token}"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read()).get("html_url")
    except OSError as e:
        raise devbus.Retry(f"forgejo unavailable: {e}", delay=3)


async def on_ticket(ev, ctx):
    d = ev["data"]
    db = _db(ctx.state_dir)
    db.execute("INSERT OR IGNORE INTO tickets VALUES (?,?,?,?,?)", (d["request_id"], d["team"], json.dumps(d["request"]), d.get("then", ""), "open"))
    db.commit()
    link = open_forgejo_issue(d["request_id"], d["team"], d["request"], d.get("sla_minutes", 0))
    with open(os.environ.get("TICKETS_FILE", os.path.join(ctx.state_dir, "tickets.jsonl")), "a") as f:
        f.write(json.dumps({"request_id": d["request_id"], "team": d["team"], "sla_minutes": d.get("sla_minutes", 0), "issue": link, "at": devbus.now()}) + "\n")
    return []


async def on_action(ev, ctx):
    """Handles infra.approval.<id> and infra.completion.<id>."""
    rid = ev["correlationid"]
    db = _db(ctx.state_dir)
    row = db.execute("SELECT request, then_runner, state FROM tickets WHERE rid=?", (rid,)).fetchone()
    if not row:
        raise devbus.PermanentError(f"no open ticket for request {rid}")
    request, then_runner, state = json.loads(row[0]), row[1], row[2]
    kind = ev["type"].split(".")[1]
    by = ev["data"].get("by", "unknown")
    if state != "open":
        return []
    db.execute("UPDATE tickets SET state=? WHERE rid=?", (kind, rid))
    db.commit()
    if kind == "approval" and then_runner:
        work = devbus.new_event(f"infra.work.{then_runner}", {"request_id": rid, "request": request, "route": "approved-by-human", "approved_by": by},
                                source=f"worker/{NAME}", parent=ev, event_id=devbus.derived_id(ev["id"], "work"))
        st = devbus.new_event("infra.status", {"request_id": rid, "state": "approved", "by": by}, source=f"worker/{NAME}", parent=ev,
                              event_id=devbus.derived_id(ev["id"], "status"))
        return [(f"infra.status.{rid}", st), (f"infra.work.{then_runner}", work)]
    res = devbus.new_event("infra.result", {"request_id": rid, "state": "done", "by": f"human:{by}"}, source=f"worker/{NAME}", parent=ev,
                           event_id=devbus.derived_id(ev["id"], "result"))
    return [(f"infra.result.{rid}", res)]


if __name__ == "__main__":
    import asyncio

    async def both():
        nc, js = await devbus.connect()
        await asyncio.gather(devbus.run_worker(NAME + "-tickets", "infra.human.>", on_ticket, js=js),
                             devbus.run_worker(NAME + "-actions", "infra.approval.*", on_action, js=js),
                             devbus.run_worker(NAME + "-completions", "infra.completion.*", on_action, js=js))

    try:
        asyncio.run(both())
    except KeyboardInterrupt:
        pass
