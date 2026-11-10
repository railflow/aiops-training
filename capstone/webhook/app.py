"""Forgejo webhook receiver for the capstone: verify the HMAC signature, then START or SIGNAL a Temporal workflow. No business logic lives here.

Routes (all decisions are in `route()`, a pure function with tests):
  push to the default branch            -> start MeasureRepoWorkflow   (id measure-<repo>-<sha12>)
  issue gets label ai-fix               -> start FixIssueWorkflow       (id fix-<repo>-<issue>)
  pull request review approved          -> signal improve-<repo> `human_approval`
  POST /ci-finished (signed, from CI)   -> signal improve-<repo> `ci_finished`
Deterministic workflow ids make redelivery harmless: Temporal returns the existing run instead of starting a duplicate.

Signature: Forgejo signs the raw body with HMAC-SHA256 using the webhook secret. The header name differs between versions and compat modes
(X-Forgejo-Signature / X-Gitea-Signature carry plain hex; X-Hub-Signature-256 carries "sha256=<hex>"). All three are accepted. Check Recent
Deliveries in the repo's webhook settings to see what YOUR Forgejo sends: these names and the event names below are from memory, not verified on Forgejo 11.
"""
import hashlib
import hmac
import json
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from fastapi import FastAPI, HTTPException, Request

SIG_HEADERS = ("x-forgejo-signature", "x-gitea-signature", "x-hub-signature-256")
EVENT_HEADERS = ("x-forgejo-event", "x-gitea-event", "x-github-event")
DELIVERY_HEADERS = ("x-forgejo-delivery", "x-gitea-delivery", "x-github-delivery")


@dataclass
class Action:
    kind: str                      # "start" or "signal"
    workflow: str = ""             # workflow type (start)
    workflow_id: str = ""
    args: Any = None
    signal: str = ""


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def signature_ok(secret: str, headers, body: bytes) -> bool:
    want = sign(secret, body)
    for h in SIG_HEADERS:
        got = headers.get(h)
        if got and hmac.compare_digest(got.removeprefix("sha256=").strip().lower(), want):
            return True
    return False


def first(headers, names) -> str:
    return next((headers[n] for n in names if headers.get(n)), "")


def route(event: str, p: dict) -> Optional[Action]:
    repo = (p.get("repository") or {}).get("full_name", "")
    if not repo:
        return None
    safe = repo.replace("/", "-")
    default = (p.get("repository") or {}).get("default_branch", "main")
    if event == "push" and p.get("ref") == f"refs/heads/{default}" and p.get("after", "0" * 40) != "0" * 40:
        sha = p["after"]
        return Action("start", "MeasureRepoWorkflow", f"measure-{safe}-{sha[:12]}", {"repo": repo, "commit_sha": sha, "reason": "push-to-default"})
    if event in ("issues", "issue_label") and p.get("action") in ("labeled", "label_updated"):
        issue = p.get("issue") or {}
        if "ai-fix" in {l.get("name") for l in issue.get("labels", [])}:
            return Action("start", "FixIssueWorkflow", f"fix-{safe}-{issue.get('number')}", {"repo": repo, "issue_number": issue.get("number")})
    if event in ("pull_request_approved", "pull_request_review_approved"):
        pr = p.get("pull_request") or {}
        return Action("signal", workflow_id=f"improve-{safe}", signal="human_approval", args={"pr": pr.get("number"), "reviewer": (p.get("sender") or {}).get("login", "")})
    return None


class Dispatcher(Protocol):
    async def start(self, workflow: str, workflow_id: str, arg: Any) -> str: ...
    async def signal(self, workflow_id: str, name: str, arg: Any) -> None: ...


@dataclass
class RecordingDispatcher:
    started: list = field(default_factory=list)
    signalled: list = field(default_factory=list)

    async def start(self, workflow, workflow_id, arg):
        self.started.append((workflow, workflow_id, arg))
        return workflow_id

    async def signal(self, workflow_id, name, arg):
        self.signalled.append((workflow_id, name, arg))


class TemporalDispatcher:
    def __init__(self):
        self._client = None

    async def client(self):
        if self._client is None:
            from temporalio.client import Client
            self._client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "temporal-frontend.temporal.svc.cluster.local:7233"),
                                                namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"))
        return self._client

    async def start(self, workflow, workflow_id, arg):
        from temporalio.common import WorkflowIDConflictPolicy
        c = await self.client()
        h = await c.start_workflow(workflow, arg, id=workflow_id, task_queue=os.environ.get("TASK_QUEUE", "capstone"),
                                   id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING)
        return h.id

    async def signal(self, workflow_id, name, arg):
        c = await self.client()
        await c.get_workflow_handle(workflow_id).signal(name, arg)


def create_app(secret: Optional[str] = None, dispatcher: Optional[Dispatcher] = None) -> FastAPI:
    secret = secret if secret is not None else os.environ.get("WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is not set: refusing to run an unauthenticated webhook receiver")
    disp = dispatcher or TemporalDispatcher()
    seen: "OrderedDict[str, bool]" = OrderedDict()      # delivery ids, to drop an exact redelivery cheaply
    app = FastAPI(title="capstone-webhook")

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/forgejo")
    async def forgejo(request: Request):
        body = await request.body()
        if not signature_ok(secret, request.headers, body):
            raise HTTPException(401, "bad or missing signature")
        event, delivery = first(request.headers, EVENT_HEADERS), first(request.headers, DELIVERY_HEADERS)
        if delivery and delivery in seen:
            return {"status": "duplicate-delivery"}
        if delivery:
            seen[delivery] = True
            while len(seen) > 1000:
                seen.popitem(last=False)
        try:
            payload = json.loads(body)
        except ValueError:
            raise HTTPException(400, "body is not JSON")
        act = route(event, payload)
        if act is None:
            return {"status": "ignored", "event": event}
        if act.kind == "start":
            wid = await disp.start(act.workflow, act.workflow_id, act.args)
            return {"status": "started", "workflow_id": wid}
        await disp.signal(act.workflow_id, act.signal, act.args)
        return {"status": "signalled", "workflow_id": act.workflow_id}

    @app.post("/ci-finished")
    async def ci_finished(request: Request):
        """Called by the last step of the repo's CI workflow with the same HMAC scheme: {"repo": "org/name", "run_id": "...", "sha": "...", "status": "success|failure"}."""
        body = await request.body()
        if not signature_ok(secret, request.headers, body):
            raise HTTPException(401, "bad or missing signature")
        j = json.loads(body)
        await disp.signal("improve-" + j["repo"].replace("/", "-"), "ci_finished", {"run_id": j["run_id"], "sha": j["sha"], "status": j["status"]})
        return {"status": "signalled"}

    return app


def app_factory() -> FastAPI:          # uvicorn app:app_factory --factory
    return create_app()
