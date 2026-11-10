#!/usr/bin/env python3
"""`platform request ...`: the front door for infrastructure requests, backed by the bus. Called by day-10-local-platform/platform/platform.

  platform request kinds                                       what can I ask for? (reads routes.yaml)
  platform request <kind> --name orders --owner alice --env dev [--set key=value ...] [--id ID] [--wait [--timeout 60]]
  platform request status <id>                                 every state change so far, in order
  platform request approve <id> --by alice                     a human approves a request that is waiting-on-human
  platform request complete <id> --by alice                    a human did the job by hand

The request id doubles as the correlation id. Pass --id to make the command safe to re-run: the same id publishes the same event id, and the
stream drops the duplicate (Nats-Msg-Id). Needs: python3, `pip install nats-py pyyaml`, NATS_URL (default nats://127.0.0.1:4222).
"""
import argparse
import asyncio
import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lab3-infra-router"))

try:
    import devbus
    import router
except ImportError as e:  # nats-py / pyyaml missing
    sys.exit(f"error: {e}. Try: python3 -m venv .venv && . .venv/bin/activate && pip install nats-py pyyaml")

TERMINAL = {"done", "rejected", "failed"}


def parse_kv(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            sys.exit(f"error: --set wants key=value, got {it!r}")
        k, v = it.split("=", 1)
        out[k] = v
    return out


async def read_events(js, rid):
    sub = await js.pull_subscribe(f"infra.*.{rid}", stream=devbus.STREAM)
    out = []
    while True:
        try:
            msgs = await sub.fetch(50, timeout=0.5)
        except Exception:
            break
        for m in msgs:
            out.append(json.loads(m.data))
            await m.ack()
    await sub.unsubscribe()
    return sorted(out, key=lambda e: e["time"])


def render(events):
    lines = []
    for e in events:
        d = e["data"]
        extra = {k: v for k, v in d.items() if k not in ("request_id", "state")}
        lines.append(f"{e['time']}  {d.get('state', e['type']):<18} {json.dumps(extra) if extra else ''}".rstrip())
    return "\n".join(lines)


async def cmd_request(a):
    nc, js = await devbus.connect()
    await devbus.ensure_stream(js)
    rid = a.id or uuid.uuid4().hex[:12]
    data = {"name": a.name, "owner": a.owner, "env": a.env, "requested_by": os.environ.get("USER", "unknown"), "params": parse_kv(a.set)}
    ev = devbus.new_event(f"infra.request.{a.kind}", data, source="cli/platform", event_id=devbus.derived_id(rid, "request"))
    ev["correlationid"] = rid
    ev["subject"] = f"{a.kind}/{a.name}"
    await devbus.publish(js, f"infra.request.{a.kind}", ev)
    print(f"request {rid} submitted ({a.kind}). Check it: platform request status {rid}")
    code = 0
    if a.wait:
        end = time.time() + a.timeout
        shown = 0
        while time.time() < end:
            events = await read_events(js, rid)
            if len(events) > shown:
                print(render(events[shown:]))
                shown = len(events)
            if any(e["data"].get("state") in TERMINAL for e in events):
                code = 0 if events[-1]["data"].get("state") == "done" else 1
                break
            if any(e["data"].get("state") == "waiting-on-human" for e in events):
                print("waiting on a human; this command stops waiting. Re-check with: platform request status " + rid)
                break
            await asyncio.sleep(0.5)
        else:
            print("timed out waiting; the request is still in flight", file=sys.stderr)
            code = 2
    await nc.close()
    return code


async def cmd_status(a):
    nc, js = await devbus.connect()
    events = await read_events(js, a.id)
    await nc.close()
    if not events:
        print(f"no events for {a.id}: wrong id, or the router has not seen it yet", file=sys.stderr)
        return 1
    print(render(events))
    return 0


async def cmd_act(a, kind):
    nc, js = await devbus.connect()
    ev = devbus.new_event(f"infra.{kind}", {"by": a.by}, source="cli/platform", event_id=devbus.derived_id(a.id, kind, a.by))
    ev["correlationid"] = a.id
    await devbus.publish(js, f"infra.{kind}.{a.id}", ev)
    print(f"{kind} recorded for {a.id} by {a.by}")
    await nc.close()
    return 0


def cmd_kinds():
    cfg = router.load_routes()
    seen = {}
    for r in cfg["routes"]:
        m = r.get("match", {})
        kind = m.get("kind")
        seen.setdefault(kind, []).append(f"env={m.get('env', 'any')} -> {r['action']}" + (f" ({r.get('team') or r.get('runner')})" if r["action"] != "reject" else ""))
    for k, paths in seen.items():
        print(f"{k}\n  " + "\n  ".join(paths))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "kinds":
        return cmd_kinds()
    if argv and argv[0] in ("status", "approve", "complete"):
        ap = argparse.ArgumentParser(prog=f"platform request {argv[0]}")
        ap.add_argument("id")
        if argv[0] != "status":
            ap.add_argument("--by", required=True)
        a = ap.parse_args(argv[1:])
        if argv[0] == "status":
            return asyncio.run(cmd_status(a))
        return asyncio.run(cmd_act(a, "approval" if argv[0] == "approve" else "completion"))
    ap = argparse.ArgumentParser(prog="platform request", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind")
    ap.add_argument("--name", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--env", default="dev")
    ap.add_argument("--set", action="append")
    ap.add_argument("--id")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--timeout", type=float, default=60)
    return asyncio.run(cmd_request(ap.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
