import json
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakectx import make_context  # noqa: E402
import main as probe_main  # noqa: E402


def test_reports_connected_for_a_listening_port(monkeypatch):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    monkeypatch.setenv("PROBE_TARGETS", f"127.0.0.1:{port}")
    out = json.loads(probe_main.main(make_context())["body"])
    assert out["results"][0]["connected"] is True
    srv.close()


def test_reports_dns_failure(monkeypatch):
    monkeypatch.setenv("PROBE_TARGETS", "no-such-host.invalid:80")
    out = json.loads(probe_main.main(make_context())["body"])
    assert "dns_error" in out["results"][0]


def test_ignores_request_parameters(monkeypatch):
    monkeypatch.delenv("PROBE_TARGETS", raising=False)
    out = json.loads(probe_main.main(make_context(query={"targets": "169.254.169.254:80"}))["body"])
    assert out["results"] == []
