import api


def client():
    api.app.config["TESTING"] = True
    return api.app.test_client()


def test_hello_default():
    body = client().get("/hello").get_json()
    assert body["message"] == "Hello, world!"
    assert body["served_by"] == "python"


def test_hello_with_name():
    assert client().get("/hello?name=Ada").get_json()["message"] == "Hello, Ada!"


def test_healthz():
    assert client().get("/healthz").get_json() == {"status": "ok"}


def test_readyz_without_database(monkeypatch):
    monkeypatch.delenv("PGHOST", raising=False)
    resp = client().get("/readyz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ready"


def test_readyz_fails_when_database_unreachable(monkeypatch):
    monkeypatch.setenv("PGHOST", "127.0.0.1")
    monkeypatch.setenv("PGPORT", "1")
    monkeypatch.setenv("PGCONNECT_TIMEOUT", "1")
    resp = client().get("/readyz")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "not ready"


def test_version_reports_build(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("GIT_SHA", "abc1234")
    body = client().get("/version").get_json()
    assert body == {"service": "hello-py", "version": "1.2.3", "commit": "abc1234"}


def test_greetings_in_memory(monkeypatch):
    monkeypatch.delenv("PGHOST", raising=False)
    api._memory.clear()
    c = client()
    assert c.post("/greetings?name=Ada").status_code == 201
    stored = c.get("/greetings").get_json()["greetings"]
    assert stored[-1]["message"] == "Hello, Ada!"


def test_relay_reports_bad_gateway_when_java_is_down(monkeypatch):
    monkeypatch.setenv("JAVA_API_URL", "http://127.0.0.1:9")
    resp = client().get("/relay")
    assert resp.status_code == 502
