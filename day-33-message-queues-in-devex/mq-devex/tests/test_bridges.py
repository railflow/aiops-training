"""Lab 5: webhook bridges. Pure mapping + signature tests, plus one run through a real nats-server."""
import asyncio
import json

from fastapi.testclient import TestClient

import bridge
import devbus

SECRET, TOKEN = "s3cret-for-tests", "tok-for-tests"
PUSH = {"ref": "refs/heads/main", "after": "a" * 40, "repository": {"full_name": "acme/orders"}, "pusher": {"login": "alice"}}


def client(pub):
    return TestClient(bridge.create_app(pub, SECRET, TOKEN))


def post_forgejo(c, payload, event="push", delivery="d-1", secret=SECRET):
    body = json.dumps(payload).encode()
    return c.post("/forgejo", content=body, headers={"x-forgejo-event": event, "x-forgejo-delivery": delivery, "x-forgejo-signature": bridge.sign(secret, body)})


def test_forgejo_push_becomes_scm_push():
    pub = bridge.RecordingPublisher()
    r = post_forgejo(client(pub), PUSH)
    assert r.status_code == 200
    subject, ev = pub.sent[0]
    assert subject == "scm.push" and ev["data"]["sha"] == "a" * 40 and ev["subject"] == "acme/orders" and ev["specversion"] == "1.0"


def test_bad_signature_rejected():
    pub = bridge.RecordingPublisher()
    assert post_forgejo(client(pub), PUSH, secret="wrong").status_code == 401
    assert pub.sent == []


def test_same_delivery_id_gives_same_event_id():
    pub = bridge.RecordingPublisher()
    c = client(pub)
    post_forgejo(c, PUSH, delivery="same")
    post_forgejo(c, PUSH, delivery="same")
    assert pub.sent[0][1]["id"] == pub.sent[1][1]["id"]


def test_unknown_forgejo_event_ignored():
    pub = bridge.RecordingPublisher()
    assert post_forgejo(client(pub), PUSH, event="fork").json() == {"ignored": True}
    assert pub.sent == []


def test_gatus_requires_token_and_maps_state():
    pub = bridge.RecordingPublisher()
    c = client(pub)
    body = {"state": "TRIGGERED", "group": "core", "name": "api", "description": "latency", "errors": "[CONNECTED] == true"}
    auth = {"authorization": f"Bearer {TOKEN}"}
    assert c.post("/gatus", json=body).status_code == 401
    assert c.post("/gatus", json=body, headers=auth).status_code == 200
    assert pub.sent[0][0] == "alerts.gatus.triggered" and pub.sent[0][1]["subject"] == "core/api"
    assert c.post("/gatus", json={**body, "state": "RESOLVED"}, headers=auth).status_code == 200
    assert pub.sent[1][0] == "alerts.gatus.resolved"
    assert c.post("/gatus", json={**body, "state": "WEIRD"}, headers=auth).status_code == 400


def test_keep_maps_defensively():
    pub = bridge.RecordingPublisher()
    c = client(pub)
    auth = {"authorization": f"Bearer {TOKEN}"}
    assert c.post("/keep", json={"name": "HighCPU", "severity": "critical", "status": "firing", "fingerprint": "fp1"}, headers=auth).status_code == 200
    assert c.post("/keep", json={}, headers=auth).status_code == 200
    assert [s for s, _ in pub.sent] == ["alerts.keep.firing", "alerts.keep.firing"]


def test_end_to_end_through_real_nats(nats_url):
    import httpx

    async def run():
        pub = bridge.NatsPublisher(nats_url)
        app = bridge.create_app(pub, SECRET, TOKEN)
        body = json.dumps(PUSH).encode()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            for _ in range(2):
                r = await c.post("/forgejo", content=body, headers={"x-forgejo-event": "push", "x-forgejo-delivery": "same", "x-forgejo-signature": bridge.sign(SECRET, body)})
                assert r.status_code == 200
        nc, js = await devbus.connect(nats_url)
        info = await js.stream_info(devbus.STREAM)
        sub = await js.pull_subscribe("scm.>", stream=devbus.STREAM)
        msgs = await sub.fetch(5, timeout=1)
        await pub.nc.close()
        await nc.close()
        return info.state.messages, [json.loads(m.data) for m in msgs]

    n, evs = asyncio.run(run())
    assert n == 1, "the redelivered webhook was dropped by the stream's duplicate window"
    assert evs[0]["type"] == "scm.push"
