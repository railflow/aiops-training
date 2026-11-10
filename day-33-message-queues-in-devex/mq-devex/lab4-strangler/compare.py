#!/usr/bin/env python3
"""Shadow-mode judge: when a correlation id has a ci.completed from BOTH implementations, publish ci.compare.result {agree: bool}.
This is how you earn the right to flip the flag: run shadow for a week and query the agreement rate (sql/queries.sql, `shadow_agreement`)."""
import os
import sqlite3

import devbus

NAME = "ci-compare"


async def handle(ev, ctx):
    d = ev["data"]
    os.makedirs(ctx.state_dir, exist_ok=True)
    db = sqlite3.connect(os.path.join(ctx.state_dir, "compare.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS r (cid TEXT, impl TEXT, passed INTEGER, PRIMARY KEY (cid, impl))")
    db.execute("INSERT OR REPLACE INTO r VALUES (?,?,?)", (ev["correlationid"], d["impl"], int(d["passed"])))
    db.commit()
    rows = dict(db.execute("SELECT impl, passed FROM r WHERE cid=?", (ev["correlationid"],)).fetchall())
    if set(rows) != {"legacy", "new"}:
        return []
    out = devbus.new_event("ci.compare.result", {"repo": d["repo"], "sha": d["sha"], "agree": rows["legacy"] == rows["new"],
                                                  "legacy_passed": bool(rows["legacy"]), "new_passed": bool(rows["new"])},
                           source=f"worker/{NAME}", parent=ev, event_id=devbus.derived_id(ev["correlationid"], "compare"))
    return [("ci.compare.result", out)]


if __name__ == "__main__":
    devbus.main(NAME, "ci.completed", handle)
