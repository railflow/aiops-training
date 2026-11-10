#!/usr/bin/env python3
"""The join. Choreography has no conductor, so "wait for both test stages" becomes state YOU own: a tiny table keyed by correlation id.
This is the honest cost of choreography; compare with the five lines it takes in a Temporal workflow (Day 27).
Emits ci.gate.passed or ci.gate.failed exactly once per correlation id (deterministic event id + idempotent worker)."""
import json
import os
import sqlite3

import devbus

NAME = "gate"
NEEDED = {"uitest", "loadtest"}


def _db(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    db = sqlite3.connect(os.path.join(state_dir, "gate-state.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS results (cid TEXT, kind TEXT, passed INTEGER, repo TEXT, sha TEXT, PRIMARY KEY (cid, kind))")
    return db


async def handle(ev, ctx):
    kind = ev["type"].split(".")[2]  # ci.test.<kind>.completed
    d = ev["data"]
    db = _db(ctx.state_dir)
    db.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", (ev["correlationid"], kind, int(bool(d["passed"])), d["repo"], d["sha"]))
    db.commit()
    rows = db.execute("SELECT kind, passed FROM results WHERE cid=?", (ev["correlationid"],)).fetchall()
    if {k for k, _ in rows} < NEEDED:
        return []
    ok = all(p for _, p in rows)
    t = "ci.gate.passed" if ok else "ci.gate.failed"
    out = devbus.new_event(t, {"repo": d["repo"], "sha": d["sha"], "results": {k: bool(p) for k, p in rows}}, source=f"worker/{NAME}", parent=ev,
                           event_id=devbus.derived_id(ev["correlationid"], "gate"))
    return [(t, out)]


if __name__ == "__main__":
    devbus.main(NAME, "ci.test.*.completed", handle)
