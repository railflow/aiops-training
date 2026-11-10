import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as patch_app  # noqa: E402


def client():
    return patch_app.app.test_client()


def test_index_reports_library_versions():
    body = client().get("/").get_json()
    assert body["app"] == "patch-demo"
    assert set(body["libs"]) == {"flask", "requests", "urllib3", "jinja2"}


def test_healthz():
    assert client().get("/healthz").get_json() == {"status": "ok"}


def test_version_defaults(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert client().get("/version").get_json() == {"version": "dev", "git_sha": "unknown"}
