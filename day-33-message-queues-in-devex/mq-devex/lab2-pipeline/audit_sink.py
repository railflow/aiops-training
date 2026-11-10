#!/usr/bin/env python3
"""Audit sink: a durable consumer of EVERYTHING in the stream, writing one row per event to JSONL and/or ClickHouse (table bus.events, sql/001_bus_events.sql).
This one worker gives you the correlation-id trace, stage latencies, and the DLQ count without any other worker knowing it exists.
ClickHouse env: CLICKHOUSE_URL, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD (from a Secret in the cluster). Rows are inserted, never updated."""
import base64
import json
import os
import urllib.parse
import urllib.request

import devbus

NAME = "audit-sink"


def to_row(ev: dict) -> dict:
    return {"event_time": ev["time"], "event_id": ev["id"], "correlation_id": ev["correlationid"], "causation_id": ev.get("causationid", ""),
            "type": ev["type"], "source": ev["source"], "entity": ev.get("subject", ""), "data": json.dumps(ev["data"], separators=(",", ":"))}


def clickhouse_insert(rows, table="bus.events"):
    url = os.environ.get("CLICKHOUSE_URL")
    if not url:
        return
    q = urllib.parse.urlencode({"query": f"INSERT INTO {table} FORMAT JSONEachRow", "date_time_input_format": "best_effort"})
    req = urllib.request.Request(url.rstrip("/") + "/?" + q, data="\n".join(json.dumps(r) for r in rows).encode(), method="POST")
    user, pw = os.environ.get("CLICKHOUSE_USER", "default"), os.environ.get("CLICKHOUSE_PASSWORD", "")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except OSError as e:
        raise devbus.Retry(f"clickhouse insert failed: {e}", delay=2)


async def handle(ev, ctx):
    row = to_row(ev)
    path = os.environ.get("AUDIT_JSONL", os.path.join(ctx.state_dir, "events.jsonl"))
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")
    clickhouse_insert([row])
    return []


if __name__ == "__main__":
    devbus.main(NAME, ">", handle)
