"""devbus.py: the small shared library every lab uses. One envelope, one worker loop, one place where retries, DLQ and idempotency live.

Envelope: a CloudEvents-1.0-shaped JSON object (specversion, id, source, type, time, subject, datacontenttype, data) plus two extension
attributes, `correlationid` (the whole business story) and `causationid` (the event that directly caused this one).
Subjects: dotted, most general first, e.g. ci.build.completed, infra.request.k8s-namespace. The subject is the routing key; `type` repeats it.

Delivery model: JetStream, at-least-once. A worker must therefore be idempotent. This loop gives you two safety nets:
  1. a processed-ids table (sqlite), so a redelivered event is acknowledged without running the handler again, and
  2. deterministic output ids plus the Nats-Msg-Id header, so JetStream drops a duplicate publish if the worker crashed between
     "publish result" and "mark done".
Failures: handler raises Retry (or any other exception) -> nak with a delay, up to max_deliver; PermanentError -> straight to dlq.<subject>.

Run any worker module directly:  python3 -m workers.build_gate  (see each lab's README). NATS_URL defaults to nats://127.0.0.1:4222.
"""
import asyncio
import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Iterable, Optional

import nats
from nats.js.api import AckPolicy, ConsumerConfig, StreamConfig

STREAM = os.environ.get("DEVBUS_STREAM", "DEVEX")
STREAM_SUBJECTS = ["ci.>", "infra.>", "scm.>", "alerts.>", "dlq.>"]
NS = uuid.UUID("6f1a2b3c-0000-4000-8000-00000000d3b5")  # fixed namespace for deterministic ids; not a secret


class PermanentError(Exception):
    """The input can never succeed (bad schema, unknown type). Do not retry: send it to the dead-letter subject."""


class Retry(Exception):
    """Transient failure (network, 503). JetStream redelivers after `delay` seconds."""

    def __init__(self, msg="retry", delay: float = 1.0):
        super().__init__(msg)
        self.delay = delay


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_event(type_: str, data: dict, source: str, parent: Optional[dict] = None, subject: str = "", event_id: Optional[str] = None) -> dict:
    """Build an envelope. With a parent, correlation is inherited and causation points at the parent's id."""
    cid = (parent or {}).get("correlationid") or uuid.uuid4().hex
    return {
        "specversion": "1.0",
        "id": event_id or uuid.uuid4().hex,
        "source": source,
        "type": type_,
        "time": now(),
        "subject": subject,
        "datacontenttype": "application/json",
        "correlationid": cid,
        "causationid": (parent or {}).get("id", ""),
        "data": data,
    }


def derived_id(parent_id: str, out_type: str, key: str = "") -> str:
    """The same input event always produces the same output id, so a re-run publishes the same Nats-Msg-Id and JetStream dedupes it."""
    return uuid.uuid5(NS, f"{parent_id}|{out_type}|{key}").hex


REQUIRED = ("specversion", "id", "source", "type", "time", "correlationid", "data")


def validate(ev: dict) -> None:
    if not isinstance(ev, dict):
        raise PermanentError("envelope must be a JSON object")
    missing = [k for k in REQUIRED if k not in ev]
    if missing:
        raise PermanentError(f"envelope missing {missing}")
    if ev["specversion"] != "1.0":
        raise PermanentError(f"unsupported specversion {ev['specversion']!r}")
    if not isinstance(ev["data"], dict):
        raise PermanentError("data must be a JSON object")


def log(worker: str, level: str, msg: str, ev: Optional[dict] = None, **extra) -> None:
    rec = {"ts": now(), "level": level, "worker": worker, "msg": msg}
    if ev:
        rec.update({"correlationid": ev.get("correlationid", ""), "event_id": ev.get("id", ""), "type": ev.get("type", "")})
    rec.update(extra)
    print(json.dumps(rec), file=sys.stderr, flush=True)


class Seen:
    """Processed-ids table. Production: put it in the same database transaction as the side effect. Here: sqlite, one file per worker."""

    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, at TEXT)")
        self.db.commit()

    def has(self, event_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM seen WHERE id=?", (event_id,)).fetchone() is not None

    def add(self, event_id: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO seen VALUES (?, ?)", (event_id, now()))
        self.db.commit()


@dataclass
class Ctx:
    """What a handler gets besides the event."""
    worker: str
    js: object
    delivered: int
    state_dir: str
    extra: dict = field(default_factory=dict)


Handler = Callable[[dict, Ctx], Awaitable[Optional[Iterable[tuple]]]]
# A handler returns None or an iterable of (subject, event) pairs to publish.


async def connect(url: Optional[str] = None):
    nc = await nats.connect(url or os.environ.get("NATS_URL", "nats://127.0.0.1:4222"), connect_timeout=5)
    return nc, nc.jetstream()


async def ensure_stream(js, name: str = STREAM, subjects: Optional[list] = None, replicas: int = 1) -> None:
    cfg = StreamConfig(name=name, subjects=subjects or STREAM_SUBJECTS, max_age=7 * 24 * 3600, num_replicas=replicas,
                       duplicate_window=120)
    try:
        await js.add_stream(cfg)
    except Exception:
        await js.update_stream(cfg)


async def publish(js, subject: str, ev: dict) -> None:
    """Publish with Nats-Msg-Id = event id: a duplicate publish inside the stream's duplicate window is dropped by the server."""
    await js.publish(subject, json.dumps(ev).encode(), headers={"Nats-Msg-Id": ev["id"]})


async def run_worker(name: str, filter_subject: str, handler: Handler, *, js=None, nc_url: Optional[str] = None, stream: str = STREAM,
                     max_deliver: int = 4, ack_wait: float = 10.0, state_dir: Optional[str] = None, stop: Optional[asyncio.Event] = None,
                     batch: int = 5, backoff: float = 1.0) -> None:
    """Pull loop for one durable consumer. `name` is the durable name: two processes with the same name share the work (a queue group)."""
    own = None
    if js is None:
        own, js = await connect(nc_url)
    state_dir = state_dir or os.environ.get("STATE_DIR", ".state")
    os.makedirs(state_dir, exist_ok=True)
    seen = Seen(os.path.join(state_dir, f"{name}.sqlite"))
    try:
        await js.stream_info(stream)
    except Exception:  # first worker up creates the stream, so start order does not matter
        await ensure_stream(js, name=stream)
    cfg = ConsumerConfig(durable_name=name, ack_policy=AckPolicy.EXPLICIT, ack_wait=ack_wait, max_deliver=max_deliver, filter_subject=filter_subject)
    sub = await js.pull_subscribe(filter_subject, durable=name, stream=stream, config=cfg)
    stop = stop or asyncio.Event()
    log(name, "info", "started", filter=filter_subject)
    while not stop.is_set():
        try:
            msgs = await sub.fetch(batch, timeout=1)
        except Exception:  # fetch timeout: nothing to do right now
            continue
        for m in msgs:
            await _one(name, m, handler, js, seen, state_dir, max_deliver, backoff)
    if own is not None:
        await own.close()


async def _one(name, m, handler, js, seen, state_dir, max_deliver, backoff):
    delivered = m.metadata.num_delivered
    try:
        ev = json.loads(m.data)
        validate(ev)
    except (ValueError, PermanentError) as e:
        await _dead_letter(js, name, m, None, f"bad envelope: {e}")
        return
    if seen.has(ev["id"]):
        log(name, "info", "duplicate delivery, already processed", ev, delivered=delivered)
        await m.ack()
        return
    try:
        outputs = await handler(ev, Ctx(name, js, delivered, state_dir)) or []
        for subject, out in outputs:
            await publish(js, subject, out)
        seen.add(ev["id"])
        await m.ack()
        log(name, "info", "done", ev, delivered=delivered, published=[s for s, _ in outputs])
    except PermanentError as e:
        await _dead_letter(js, name, m, ev, str(e))
    except Exception as e:  # Retry or anything unexpected
        delay = getattr(e, "delay", backoff * delivered)
        if delivered >= max_deliver:
            await _dead_letter(js, name, m, ev, f"gave up after {delivered} deliveries: {e}")
        else:
            log(name, "warn", f"failed, will redeliver in {delay:.1f}s: {e}", ev, delivered=delivered)
            await m.nak(delay=delay)


async def _dead_letter(js, name, m, ev, reason):
    parent = ev or {"correlationid": "unknown", "id": ""}
    key = parent.get("id", "") or uuid.uuid4().hex
    dead = new_event("devex.dlq.entry", {"worker": name, "subject": m.subject, "reason": reason, "original": ev or m.data.decode("utf-8", "replace")},
                     source=f"worker/{name}", parent=parent, event_id=derived_id(key, "dlq", name))
    await publish(js, "dlq." + m.subject, dead)
    await m.term()
    log(name, "error", f"dead-lettered: {reason}", ev, subject=m.subject)


def main(name: str, filter_subject: str, handler: Handler, **kw) -> None:
    """Entry point for `python3 -m workers.<module>`: run until Ctrl-C."""
    try:
        asyncio.run(run_worker(name, filter_subject, handler, **kw))
    except KeyboardInterrupt:
        pass


def wait_until(predicate, timeout: float = 10.0, interval: float = 0.05) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False
