"""Tiny service whose only job is to say exactly which dependency versions it runs."""
import os
from importlib.metadata import version

from flask import Flask, jsonify

app = Flask(__name__)


def versions():
    return {name: version(name) for name in ("flask", "requests", "urllib3", "jinja2")}


@app.get("/")
def index():
    return jsonify(app="patch-demo", libs=versions())


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/version")
def app_version():
    return jsonify(version=os.environ.get("APP_VERSION", "dev"), git_sha=os.environ.get("GIT_SHA", "unknown"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
