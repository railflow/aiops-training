import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as starter  # noqa: E402


def test_health_and_version(monkeypatch):
    monkeypatch.delenv("PGHOST", raising=False)
    c = starter.app.test_client()
    assert c.get("/healthz").status_code == 200
    assert c.get("/readyz").status_code == 200
    assert c.get("/version").get_json()["version"] == "dev"


def test_not_ready_when_database_is_unreachable(monkeypatch):
    monkeypatch.setenv("PGHOST", "127.0.0.1")
    monkeypatch.setenv("PGPORT", "1")
    assert starter.app.test_client().get("/readyz").status_code == 503
