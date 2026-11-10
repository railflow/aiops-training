#!/usr/bin/env python3
"""The request router: ONE small service that turns "somebody needs infrastructure" into the right path (automation or a named team of humans).
Requesters publish infra.request.<kind> and never learn who does the work. Add a path = add a rule here (routes.yaml) and a worker that listens.

Events it publishes (all keep the request's correlation id, which is also the request id):
  infra.work.<runner>        for automation (e.g. terraform_runner.py listens on infra.work.terraform)
  infra.human.<team>         for a human team (human_desk.py turns it into a ticket)
  infra.status.<request-id>  every state change, so `platform request status <id>` can show where it is
"""
import os
from typing import Optional

import yaml

import devbus

NAME = "router"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_routes(path: Optional[str] = None) -> dict:
    with open(path or os.environ.get("ROUTES_FILE", os.path.join(HERE, "routes.yaml"))) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict) or "routes" not in cfg:
        raise ValueError("routes file needs a top-level 'routes' list")
    return cfg


def matches(match: dict, data: dict) -> bool:
    for key, want in match.items():
        have = data.get(key)
        ok = have in want if isinstance(want, list) else have == want
        if not ok:
            return False
    return True


def decide(data: dict, cfg: dict) -> dict:
    """Pure function: request data in, decision out. This is the part you unit-test; there is no NATS in it."""
    for r in cfg["routes"]:
        if matches(r.get("match", {}), data):
            missing = [k for k in r.get("require", []) if not data.get(k)]
            if missing:
                return {"action": "reject", "route": r["name"], "reason": f"missing required fields: {', '.join(missing)}"}
            return {**r, "route": r["name"]}
    return {**cfg.get("default", {"action": "reject", "reason": "no route"}), "route": "default"}


def status(parent, request_id, state, **detail):
    ev = devbus.new_event("infra.status", {"request_id": request_id, "state": state, **detail}, source=f"worker/{NAME}", parent=parent,
                          event_id=devbus.derived_id(parent["id"], "status", state))
    return (f"infra.status.{request_id}", ev)


async def handle(ev, ctx):
    data = dict(ev["data"])
    kind = ev["type"].split(".", 2)[2] if ev["type"].count(".") >= 2 else ""
    data.setdefault("kind", kind)
    rid = ev["correlationid"]
    d = decide(data, load_routes())
    if d["action"] == "reject":
        return [status(ev, rid, "rejected", reason=d.get("reason", ""), route=d["route"])]
    if d["action"] == "automate":
        work = devbus.new_event(f"infra.work.{d['runner']}", {"request_id": rid, "request": data, "route": d["route"]}, source=f"worker/{NAME}", parent=ev,
                                event_id=devbus.derived_id(ev["id"], "work"))
        return [status(ev, rid, "routed", route=d["route"], via="automation", runner=d["runner"]), (f"infra.work.{d['runner']}", work)]
    if d["action"] == "human":
        ticket = devbus.new_event(f"infra.human.{d['team']}", {"request_id": rid, "request": data, "route": d["route"], "team": d["team"],
                                                               "sla_minutes": d.get("sla_minutes", 0), "then": d.get("then", "")},
                                  source=f"worker/{NAME}", parent=ev, event_id=devbus.derived_id(ev["id"], "human"))
        return [status(ev, rid, "waiting-on-human", route=d["route"], team=d["team"], sla_minutes=d.get("sla_minutes", 0)), (f"infra.human.{d['team']}", ticket)]
    raise devbus.PermanentError(f"route {d['route']!r} has unknown action {d['action']!r}")


if __name__ == "__main__":
    devbus.main(NAME, "infra.request.>", handle)
