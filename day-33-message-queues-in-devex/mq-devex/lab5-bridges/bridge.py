"""Webhook-to-bus bridge: the ONLY place that knows about vendor payload shapes. Everything behind it sees one envelope.

  POST /forgejo   Forgejo webhook, HMAC-SHA256 signed with the webhook secret          -> scm.push | scm.pull_request | scm.issue
  POST /keep      Keep HQ workflow webhook, shared bearer token                          -> alerts.keep.<status>
  POST /gatus     Gatus `alerting.custom` webhook, shared bearer token                   -> alerts.gatus.<triggered|resolved>
  GET  /healthz

Why a bridge instead of every consumer exposing a webhook: one signature check, one place to rate-limit, and a retried delivery cannot become
a duplicate because the event id is derived from the delivery id (so JetStream's Msg-Id dedupe drops it).

Environment: BRIDGE_FORGEJO_SECRET, BRIDGE_TOKEN (both from Secrets, never in git), NATS_URL.
Payload-shape caveats: the Gatus body is the template shown in README.md (placeholders verified in Gatus's README). Forgejo header and event names are
the same unverified-on-Forgejo-11 assumptions as the capstone's webhook. The Keep payload shape is an ASSUMPTION: the mapper only reads name, severity,
status, fingerprint, description, and falls back to blanks; check a real delivery and adjust `map_keep`.
"""
import hashlib
import hmac
import json
import os
import sys
from typing import Optional, Protocol

from fastapi import FastAPI, HTTPException, Request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import devbus  # noqa: E402

SIG_HEADERS = ("x-forgejo-signature", "x-gitea-signature", "x-hub-signature-256")
EVENT_HEADERS = ("x-forgejo-event", "x-gitea-event", "x-github-event")
DELIVERY_HEADERS = ("x-forgejo-delivery", "x-gitea-delivery", "x-github-delivery")


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def signature_ok(secret: str, headers, body: bytes) -> bool:
    want = sign(secret, body)
    return any(headers.get(h) and hmac.compare_digest(headers[h].removeprefix("sha256=").strip().lower(), want) for h in SIG_HEADERS)


def first(headers, names) -> str:
    return next((headers[n] for n in names if headers.get(n)), "")


def map_forgejo(event: str, p: dict) -> Optional[tuple]:
    """-> (subject, entity, data) or None when we do not care about this event."""
    repo = (p.get("repository") or {}).get("full_name", "")
    if not repo:
        return None
    if event == "push":
        return ("scm.push", repo, {"repo": repo, "ref": p.get("ref", ""), "sha": p.get("after", ""), "pusher": (p.get("pusher") or {}).get("login", "")})
    if event == "pull_request":
        pr = p.get("pull_request") or {}
        return ("scm.pull_request", f"{repo}#{pr.get('number')}", {"repo": repo, "number": pr.get("number"), "action": p.get("action", ""), "title": pr.get("title", "")})
    if event in ("issues", "issue_label"):
        i = p.get("issue") or {}
        return ("scm.issue", f"{repo}#{i.get('number')}", {"repo": repo, "number": i.get("number"), "action": p.get("action", ""), "labels": [l.get("name") for l in i.get("labels", [])]})
    return None


def map_keep(p: dict) -> tuple:
    status = (p.get("status") or "firing").lower()
    return (f"alerts.keep.{status}", p.get("fingerprint", ""), {"name": p.get("name", ""), "severity": p.get("severity", ""), "status": status,
                                                                   "fingerprint": p.get("fingerprint", ""), "description": p.get("description", "")})


def map_gatus(p: dict) -> tuple:
    state = (p.get("state") or "TRIGGERED").lower()
    if state not in ("triggered", "resolved"):
        raise HTTPException(400, f"unknown state {p.get('state')!r}")
    return (f"alerts.gatus.{state}", f"{p.get('group', '')}/{p.get('name', '')}", {"group": p.get("group", ""), "name": p.get("name", ""), "state": state,
                                                                                    "description": p.get("description", ""), "errors": p.get("errors", "")})


class Publisher(Protocol):
    async def publish(self, subject: str, ev: dict) -> None: ...


class NatsPublisher:
    def __init__(self, url: Optional[str] = None):
        self.url, self.nc, self.js = url, None, None

    async def publish(self, subject, ev):
        if self.js is None:
            self.nc, self.js = await devbus.connect(self.url)
            await devbus.ensure_stream(self.js)
        await devbus.publish(self.js, subject, ev)


class RecordingPublisher:
    def __init__(self):
        self.sent = []

    async def publish(self, subject, ev):
        self.sent.append((subject, ev))


def create_app(publisher: Publisher, forgejo_secret: str, token: str) -> FastAPI:
    app = FastAPI(title="bus bridge")

    def event(subject, source, entity, data, delivery):
        key = delivery or hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return devbus.new_event(subject, data, source=source, subject=entity, event_id=devbus.derived_id(key, subject))

    def check_token(request: Request):
        got = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not token or not hmac.compare_digest(got, token):
            raise HTTPException(401, "bad or missing bearer token")

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/forgejo")
    async def forgejo(request: Request):
        body = await request.body()
        if not forgejo_secret or not signature_ok(forgejo_secret, request.headers, body):
            raise HTTPException(401, "bad signature")
        mapped = map_forgejo(first(request.headers, EVENT_HEADERS), json.loads(body or b"{}"))
        if not mapped:
            return {"ignored": True}
        subject, entity, data = mapped
        ev = event(subject, "bridge/forgejo", entity, data, first(request.headers, DELIVERY_HEADERS))
        await publisher.publish(subject, ev)
        return {"published": subject, "id": ev["id"]}

    @app.post("/keep")
    async def keep(request: Request):
        check_token(request)
        subject, entity, data = map_keep(await request.json())
        ev = event(subject, "bridge/keep", entity, data, "")
        await publisher.publish(subject, ev)
        return {"published": subject, "id": ev["id"]}

    @app.post("/gatus")
    async def gatus(request: Request):
        check_token(request)
        subject, entity, data = map_gatus(await request.json())
        ev = event(subject, "bridge/gatus", entity, data, "")
        await publisher.publish(subject, ev)
        return {"published": subject, "id": ev["id"]}

    return app


def build_app() -> FastAPI:
    return create_app(NatsPublisher(), os.environ.get("BRIDGE_FORGEJO_SECRET", ""), os.environ.get("BRIDGE_TOKEN", ""))
