import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakectx import make_context  # noqa: E402
import main as fn  # noqa: E402
import store  # noqa: E402


def body(out):
    return json.loads(out["body"])


def post(payload):
    ctx = make_context(path="/entries", body=json.dumps(payload).encode())
    return fn.main(ctx)


def test_add_and_list(monkeypatch):
    monkeypatch.setattr(fn, "_memory", store.MemoryStore())
    assert post({"name": "Ada", "message": "first"})["statusCode"] == 201
    assert post({"name": "Bob", "message": "second"})["statusCode"] == 201
    entries = body(fn.main(make_context(path="/entries")))["entries"]
    assert [e["name"] for e in entries] == ["Bob", "Ada"]


def test_validation(monkeypatch):
    monkeypatch.setattr(fn, "_memory", store.MemoryStore())
    assert post({"name": "", "message": "x"})["statusCode"] == 400
    assert post({"name": "Ada"})["statusCode"] == 400
    assert post({"name": "Ada", "message": "x" * 501})["statusCode"] == 400


def test_health_and_unknown_path():
    assert body(fn.main(make_context(path="/healthz"))) == {"status": "ok"}
    assert fn.main(make_context(path="/nope"))["statusCode"] == 404


def test_appwrite_store_builds_the_right_call():
    seen = []

    class R:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def opener(req, timeout):
        seen.append((req.get_method(), req.full_url, dict(req.header_items())))
        return R(b'{"$id": "r1"}' if req.get_method() == "POST" else b'{"rows": [{"$id": "r1", "name": "Ada", "message": "hi"}]}')

    s = store.AppwriteStore("http://x/v1/", "p1", "k1", opener=opener)
    assert s.add("Ada", "hi")["id"] == "r1"
    assert s.latest()[0]["name"] == "Ada"
    assert seen[0][1] == "http://x/v1/tablesdb/guestbook/tables/entries/rows"
    assert seen[0][2]["X-appwrite-key"] == "k1" and seen[0][2]["X-appwrite-project"] == "p1"
    assert seen[1][0] == "GET" and "queries[]=" in seen[1][1]
