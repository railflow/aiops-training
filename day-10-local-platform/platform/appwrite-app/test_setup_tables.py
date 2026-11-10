import io
import json
import urllib.error

import setup_tables as s


def test_idempotent_and_waits_for_columns(monkeypatch, capsys):
    monkeypatch.setenv("APPWRITE_ENDPOINT", "http://x/v1")
    monkeypatch.setenv("APPWRITE_PROJECT_ID", "p")
    monkeypatch.setenv("APPWRITE_API_KEY", "k")
    calls = []

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, timeout):
        calls.append((req.get_method(), req.full_url.replace("http://x/v1", "")))
        if req.get_method() == "POST" and req.full_url.endswith("/tablesdb"):
            raise urllib.error.HTTPError(req.full_url, 409, "conflict", {}, io.BytesIO(b"{}"))
        if req.get_method() == "GET":
            return R(json.dumps({"columns": [{"key": "name", "status": "available"}, {"key": "message", "status": "available"}]}).encode())
        return R(b"{}")

    monkeypatch.setattr(s.urllib.request, "urlopen", fake)
    s.main()
    assert ("POST", "/tablesdb/guestbook/tables/entries/columns/varchar") in calls
    assert "ready: name, message" in capsys.readouterr().out
