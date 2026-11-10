"""A tiny REST API.

GET  /              greeting (also /hello); optional ?name=
GET  /healthz       liveness: the process is up (no dependencies checked)
GET  /readyz        readiness: the app can serve traffic (checks Postgres when PGHOST is set)
GET  /version       which build is running (APP_VERSION and GIT_SHA environment variables)
GET  /greetings     list stored greetings (Postgres if PGHOST is set, else in memory)
POST /greetings     store a greeting: ?name=Ada or JSON {"name": "Ada"}
GET  /relay         call the Java API (JAVA_API_URL) and return both answers
"""
import os
import socket

import requests
from flask import Flask, jsonify, request

from greeter import make_greeting

app = Flask(__name__)
_memory = []


def _use_db():
    return bool(os.environ.get("PGHOST"))


def _connect():
    import psycopg2  # imported lazily so tests and in-memory mode do not need a database

    # If the password is delivered as a file (a mounted secret), read it on every new connection so a
    # rotated password is picked up without a restart. Environment variables never change after start.
    password_file = os.environ.get("PGPASSWORD_FILE")
    if password_file:
        with open(password_file, encoding="utf-8") as handle:
            return psycopg2.connect(password=handle.read().strip())
    return psycopg2.connect()


def _ensure_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS greetings (
            id         SERIAL PRIMARY KEY,
            name       TEXT        NOT NULL,
            message    TEXT        NOT NULL,
            source     TEXT        NOT NULL DEFAULT 'unknown',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


@app.get("/")
@app.get("/hello")
def hello():
    return jsonify(
        message=make_greeting(request.args.get("name")),
        served_by="python",
        pod=socket.gethostname(),
    )


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/readyz")
def readyz():
    if not _use_db():
        return jsonify(status="ready", database="not configured")
    try:
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - any failure means "not ready"; never leak details to callers
        return jsonify(status="not ready", database="unavailable"), 503
    return jsonify(status="ready", database="ok")


@app.get("/version")
def version():
    return jsonify(
        service="hello-py",
        version=os.environ.get("APP_VERSION", "dev"),
        commit=os.environ.get("GIT_SHA", "unknown"),
    )


@app.get("/greetings")
def list_greetings():
    if not _use_db():
        return jsonify(greetings=_memory[-20:])
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            _ensure_table(cur)
            cur.execute("SELECT id, source, name, message FROM greetings ORDER BY id DESC LIMIT 20")
            rows = [
                {"id": r[0], "source": r[1], "name": r[2], "message": r[3]} for r in cur.fetchall()
            ]
    finally:
        conn.close()
    return jsonify(greetings=rows)


@app.post("/greetings")
def add_greeting():
    payload = request.get_json(silent=True) or {}
    name = request.args.get("name") or payload.get("name")
    message = make_greeting(name)
    if not _use_db():
        _memory.append({"name": name, "message": message, "source": "python"})
        return jsonify(message=message, stored="memory"), 201
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            _ensure_table(cur)
            cur.execute(
                "INSERT INTO greetings (name, message, source) VALUES (%s, %s, 'python-api')",
                (name or "world", message),
            )
    finally:
        conn.close()
    return jsonify(message=message, stored="postgres"), 201


@app.get("/relay")
def relay():
    url = os.environ.get("JAVA_API_URL", "http://java-api").rstrip("/")
    try:
        resp = requests.get(f"{url}/hello", params={"name": "from-python"}, timeout=3)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return jsonify(python=socket.gethostname(), error=str(exc), target=url), 502
    return jsonify(python=socket.gethostname(), java=resp.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
