"""A tiny two-tier "shop" used for observability, monitoring and dashboard labs.

The same image runs as two deployments: shop-frontend (calls the backend) and shop-backend.

Normal endpoints
  GET /hello            greeting (cheap)
  GET /healthz          probe endpoint (not logged)
  GET /checkout         frontend: calls the backend /price, then answers (a 2-span trace)
  GET /price            backend: pretends to look a price up

Fault injection (all off by default, so a quiet system looks quiet)
  GET /flaky?rate=0.3   fails with HTTP 500 for about 30% of requests
  GET /slow?ms=800      sleeps, then answers
  Environment: INJECT_ERROR_RATE (0..1) and INJECT_LATENCY_MS add the same faults to /checkout and /price,
  so you can switch a whole deployment into "bad" mode with `kubectl set env` and no rebuild.

Resource demos (use on purpose, with a low limit; see the monitoring page)
  GET /burn?ms=200      busy-loops one CPU for that long
  GET /alloc?mb=50      allocates and KEEPS that many MB (until /free); the OOMKill demo
  GET /free             releases what /alloc kept
"""
import json
import logging
import os
import random
import socket
import sys
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import trace

SERVICE = os.environ.get("OTEL_SERVICE_NAME", "shop")
BACKEND_URL = os.environ.get("BACKEND_URL", "")

app = Flask(__name__)


class JsonFormatter(logging.Formatter):
    """One JSON object per line on stdout, with the active trace id so logs and traces join up."""

    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        doc = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": SERVICE,
            "message": record.getMessage(),
        }
        if ctx.is_valid:
            doc["trace_id"] = format(ctx.trace_id, "032x")
            doc["span_id"] = format(ctx.span_id, "016x")
        for key in ("path", "status", "duration_ms"):
            if hasattr(record, key):
                doc[key] = getattr(record, key)
        return json.dumps(doc)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("shop")
log.setLevel(logging.INFO)
log.addHandler(handler)
log.propagate = True  # also reaches the OpenTelemetry log handler on the root logger

_kept = []


def _fault_env():
    rate = float(os.environ.get("INJECT_ERROR_RATE", "0") or 0)
    latency = int(os.environ.get("INJECT_LATENCY_MS", "0") or 0)
    return rate, latency


def _maybe_fail(rate, label):
    if rate and random.random() < rate:
        log.error("injected failure in %s", label, extra={"path": request.path, "status": 500})
        return jsonify(error="injected failure", where=label, pod=socket.gethostname()), 500
    return None


@app.before_request
def _start():
    request.environ["t0"] = time.perf_counter()


@app.after_request
def _log_request(resp):
    if request.path != "/healthz":
        ms = round((time.perf_counter() - request.environ.get("t0", time.perf_counter())) * 1000, 1)
        level = logging.ERROR if resp.status_code >= 500 else logging.INFO
        log.log(level, "request", extra={"path": request.path, "status": resp.status_code, "duration_ms": ms})
    return resp


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/")
@app.get("/hello")
def hello():
    return jsonify(message="Hello from " + SERVICE, pod=socket.gethostname())


@app.get("/price")
def price():
    rate, latency = _fault_env()
    if latency:
        time.sleep(latency / 1000)
    failed = _maybe_fail(rate, "price")
    if failed:
        return failed
    time.sleep(random.uniform(0.005, 0.03))
    return jsonify(item="widget", price=round(random.uniform(5, 50), 2), pod=socket.gethostname())


@app.get("/checkout")
def checkout():
    rate, latency = _fault_env()
    if latency:
        time.sleep(latency / 1000)
    failed = _maybe_fail(rate, "checkout")
    if failed:
        return failed
    if not BACKEND_URL:
        return jsonify(error="BACKEND_URL is not set"), 500
    try:
        resp = requests.get(BACKEND_URL.rstrip("/") + "/price", timeout=3)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("backend call failed: %s", exc, extra={"path": request.path, "status": 502})
        return jsonify(error="backend call failed", detail=str(exc)), 502
    return jsonify(order="ok", price=resp.json(), pod=socket.gethostname())


@app.get("/flaky")
def flaky():
    rate = float(request.args.get("rate", "0.3"))
    failed = _maybe_fail(rate, "flaky")
    return failed or jsonify(ok=True)


@app.get("/slow")
def slow():
    time.sleep(int(request.args.get("ms", "800")) / 1000)
    return jsonify(slept_ms=int(request.args.get("ms", "800")))


@app.get("/burn")
def burn():
    end = time.perf_counter() + int(request.args.get("ms", "200")) / 1000
    while time.perf_counter() < end:
        pass
    return jsonify(burned_ms=int(request.args.get("ms", "200")))


@app.get("/alloc")
def alloc():
    mb = int(request.args.get("mb", "50"))
    block = bytearray(mb * 1024 * 1024)
    block[::4096] = b"\x01" * len(range(0, len(block), 4096))  # touch every page so it counts as used memory
    _kept.append(block)
    return jsonify(kept_mb=sum(len(b) for b in _kept) // (1024 * 1024))


@app.get("/free")
def free():
    _kept.clear()
    return jsonify(kept_mb=0)
