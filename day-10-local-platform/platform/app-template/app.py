"""Starter service. Replace the / route with your own; keep /healthz, /readyz and /version."""
import os

from flask import Flask, jsonify

app = Flask(__name__)


def db_reachable():
    """Readiness depends on the database only when the platform has provisioned one for this app."""
    if not os.environ.get("PGHOST"):
        return True
    import psycopg2

    try:
        psycopg2.connect(connect_timeout=2).close()
        return True
    except Exception:
        return False


@app.get("/")
def index():
    return jsonify(app="__APP__", message="hello from the paved road")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/readyz")
def readyz():
    ok = db_reachable()
    return jsonify(status="ready" if ok else "not ready"), (200 if ok else 503)


@app.get("/version")
def version():
    return jsonify(version=os.environ.get("APP_VERSION", "dev"), git_sha=os.environ.get("GIT_SHA", "unknown"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
