import io
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from fakectx import make_context  # noqa: E402
import main as fn  # noqa: E402


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("APPWRITE_FUNCTION_API_ENDPOINT", "http://appwrite.localhost/v1")
    monkeypatch.setenv("APPWRITE_FUNCTION_PROJECT_ID", "proj1")
    monkeypatch.delenv("APPWRITE_ENDPOINT", raising=False)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def post(name):
    return make_context(headers={"x-appwrite-key": "k"}, body=json.dumps({"name": name}).encode())


def test_writes_a_row_and_uses_the_ephemeral_key(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"], seen["headers"], seen["data"] = req.full_url, dict(req.header_items()), json.loads(req.data)
        return _Resp(b'{"$id": "abc123"}')

    monkeypatch.setattr(fn.urllib.request, "urlopen", fake_urlopen)
    out = fn.main(post("Ada"))
    assert out["statusCode"] == 201 and json.loads(out["body"]) == {"id": "abc123", "name": "Ada"}
    assert seen["url"] == "http://appwrite.localhost/v1/tablesdb/hello/tables/greetings/rows"
    assert seen["headers"]["X-appwrite-key"] == "k" and seen["data"]["data"] == {"name": "Ada"}


def test_endpoint_override_wins(monkeypatch):
    monkeypatch.setenv("APPWRITE_ENDPOINT", "http://host.example:8080/v1/")
    seen = {}
    monkeypatch.setattr(fn.urllib.request, "urlopen", lambda req, timeout: seen.setdefault("u", req.full_url) and _Resp(b"{}"))
    fn.main(post("Ada"))
    assert seen["u"].startswith("http://host.example:8080/v1/tablesdb/")


def test_rejects_bad_input():
    assert fn.main(post(""))["statusCode"] == 400
    assert fn.main(post("x" * 101))["statusCode"] == 400
    assert fn.main(make_context())["statusCode"] == 405


def test_unreachable_endpoint_is_a_clear_502(monkeypatch):
    def boom(req, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(fn.urllib.request, "urlopen", boom)
    out = fn.main(post("Ada"))
    assert out["statusCode"] == 502 and "cannot reach" in json.loads(out["body"])["error"]
