"""Lab 2 against a real nats-server: the pipeline as events, the correlation chain, redelivery after a killed consumer, idempotency, DLQ."""
import asyncio
import json
import time

import pytest

import devbus
import emit_build
import uitest, loadtest, gate, deploy, notify, audit_sink  # noqa: E401


async def read_stream(js, filter_subject=">"):
    """Return every (subject, event) currently in the stream, read by an ephemeral consumer from the beginning."""
    sub = await js.pull_subscribe(filter_subject, stream=devbus.STREAM)
    out = []
    while True:
        try:
            msgs = await sub.fetch(50, timeout=0.5)
        except Exception:
            break
        for m in msgs:
            out.append((m.subject, json.loads(m.data)))
            await m.ack()
    await sub.unsubscribe()
    return out


async def until(coro_fn, pred, timeout=15.0):
    end = time.time() + timeout
    val = None
    while time.time() < end:
        val = await coro_fn()
        if pred(val):
            return val
        await asyncio.sleep(0.2)
    raise AssertionError("condition not reached; last value: " + repr(val)[:600])


def start_all(js, state_dir, stop):
    ws = [("uitest", "ci.build.completed", uitest.handle), ("loadtest", "ci.build.completed", loadtest.handle),
          ("gate", "ci.test.*.completed", gate.handle), ("deploy", "ci.gate.passed", deploy.handle), ("notify", "ci.>", notify.handle),
          ("audit-sink", ">", audit_sink.handle)]
    return [asyncio.create_task(devbus.run_worker(n, f, h, js=js, state_dir=state_dir, stop=stop, ack_wait=3)) for n, f, h in ws]


@pytest.fixture(autouse=True)
def fast(monkeypatch, tmp_path):
    monkeypatch.setenv("UITEST_SECONDS", "0.05")
    monkeypatch.setenv("LOADTEST_SECONDS", "0.05")
    monkeypatch.setenv("NOTIFY_SINK", str(tmp_path / "notes.jsonl"))
    monkeypatch.setenv("AUDIT_JSONL", str(tmp_path / "audit.jsonl"))


def test_happy_path_chain_shares_one_correlation_id(nats_url, state_dir):
    async def run():
        nc, js = await devbus.connect(nats_url)
        stop = asyncio.Event()
        tasks = start_all(js, state_dir, stop)
        ev = await emit_build.emit(js, "orders-api", "abc1234")
        events = await until(lambda: read_stream(js), lambda evs: any(s == "ci.deploy.completed" for s, _ in evs))
        stop.set()
        await asyncio.gather(*tasks)
        await nc.close()
        return ev, events

    root, events = asyncio.run(run())
    chain = [e for s, e in events if s.startswith("ci.")]
    assert {e["correlationid"] for e in chain} == {root["correlationid"]}
    types = [e["type"] for e in chain]
    assert types[0] == "ci.build.completed"
    assert {"ci.test.uitest.completed", "ci.test.loadtest.completed", "ci.gate.passed", "ci.deploy.completed"} <= set(types)
    by_id = {e["id"]: e for e in chain}
    deploy_ev = next(e for e in chain if e["type"] == "ci.deploy.completed")
    gate_ev = by_id[deploy_ev["causationid"]]
    assert gate_ev["type"] == "ci.gate.passed"
    assert types.count("ci.gate.passed") == 1
    assert by_id[gate_ev["causationid"]]["type"].startswith("ci.test.")


def test_failed_ui_blocks_deploy_and_notifies(nats_url, state_dir, tmp_path):
    async def run():
        nc, js = await devbus.connect(nats_url)
        stop = asyncio.Event()
        tasks = start_all(js, state_dir, stop)
        await emit_build.emit(js, "orders-api", "bad0001", fail_ui=True)
        await until(lambda: read_stream(js), lambda evs: any(s == "ci.gate.failed" for s, _ in evs))
        await asyncio.sleep(1.0)
        events = await read_stream(js)
        stop.set()
        await asyncio.gather(*tasks)
        await nc.close()
        return events

    events = asyncio.run(run())
    assert not any(s == "ci.deploy.completed" for s, _ in events)
    notes = [json.loads(l) for l in open(tmp_path / "notes.jsonl")]
    assert [n["label"] for n in notes] == ["BLOCKED"]
    audit = [json.loads(l) for l in open(tmp_path / "audit.jsonl")]
    assert "ci.gate.failed" in {a["type"] for a in audit}


def test_killed_consumer_means_redelivery(nats_url, state_dir):
    """The consumer takes the message and 'crashes' before acking (we cancel its task). A replacement with the same durable name gets it again."""
    first_deliveries = []

    async def hang(ev, ctx):
        first_deliveries.append(ctx.delivered)
        await asyncio.sleep(60)

    async def run():
        nc, js = await devbus.connect(nats_url)
        t1 = asyncio.create_task(devbus.run_worker("uitest", "ci.build.completed", hang, js=js, state_dir=state_dir, ack_wait=1))
        ev = await emit_build.emit(js, "orders-api", "kill001")
        end = time.time() + 5
        while not first_deliveries and time.time() < end:
            await asyncio.sleep(0.05)
        t1.cancel()
        try:
            await t1
        except asyncio.CancelledError:
            pass
        seen = []

        async def real(ev2, ctx):
            seen.append(ctx.delivered)
            return await uitest.handle(ev2, ctx)

        stop = asyncio.Event()
        t2 = asyncio.create_task(devbus.run_worker("uitest", "ci.build.completed", real, js=js, state_dir=state_dir, ack_wait=1, stop=stop))
        events = await until(lambda: read_stream(js, "ci.test.uitest.completed"), lambda evs: len(evs) == 1)
        stop.set()
        await t2
        await nc.close()
        return ev, seen, events

    root, seen, events = asyncio.run(run())
    assert first_deliveries == [1]
    assert seen and seen[0] >= 2, "the replacement saw a REdelivery, not a first delivery"
    assert events[0][1]["correlationid"] == root["correlationid"]


def test_duplicate_event_ids_run_the_handler_once(nats_url, state_dir):
    calls = []

    async def count(ev, ctx):
        calls.append(ev["id"])

    async def run():
        nc, js = await devbus.connect(nats_url)
        ev = devbus.new_event("ci.build.completed", {"repo": "r", "sha": "s"}, "test")
        for i in range(3):  # three JetStream messages carrying the SAME event id: a producer retry the server could not dedupe
            await js.publish("ci.build.completed", json.dumps(ev).encode(), headers={"Nats-Msg-Id": f"unique-{i}"})
        stop = asyncio.Event()
        t = asyncio.create_task(devbus.run_worker("counter", "ci.build.completed", count, js=js, state_dir=state_dir, stop=stop))
        await asyncio.sleep(2.0)
        stop.set()
        await t
        await nc.close()

    asyncio.run(run())
    assert len(calls) == 1


def test_server_side_dedupe_by_msg_id(nats_url):
    async def run():
        nc, js = await devbus.connect(nats_url)
        ev = devbus.new_event("ci.build.completed", {"repo": "r", "sha": "s"}, "test")
        acks = [await js.publish("ci.build.completed", json.dumps(ev).encode(), headers={"Nats-Msg-Id": ev["id"]}) for _ in range(3)]
        info = await js.stream_info(devbus.STREAM)
        await nc.close()
        return acks, info.state.messages

    acks, n = asyncio.run(run())
    assert n == 1 and [bool(a.duplicate) for a in acks] == [False, True, True]


def test_bad_envelope_and_exhausted_retries_go_to_dlq(nats_url, state_dir):
    async def always_503(ev, ctx):
        raise devbus.Retry("503 from webhook", delay=0.2)

    async def run():
        nc, js = await devbus.connect(nats_url)
        await js.publish("ci.build.completed", b'{"hello": "world"}')
        good = devbus.new_event("ci.deploy.requested", {"repo": "r", "sha": "s"}, "test")
        await devbus.publish(js, "ci.deploy.requested", good)
        stop = asyncio.Event()
        t1 = asyncio.create_task(devbus.run_worker("w-bad", "ci.build.completed", uitest.handle, js=js, state_dir=state_dir, stop=stop))
        t2 = asyncio.create_task(devbus.run_worker("w-503", "ci.deploy.requested", always_503, js=js, state_dir=state_dir, stop=stop, max_deliver=3))
        dlq = await until(lambda: read_stream(js, "dlq.>"), lambda evs: len(evs) == 2, timeout=20)
        stop.set()
        await asyncio.gather(t1, t2)
        await nc.close()
        return dlq

    dlq = dict(asyncio.run(run()))
    assert "bad envelope" in dlq["dlq.ci.build.completed"]["data"]["reason"]
    assert "gave up after 3 deliveries" in dlq["dlq.ci.deploy.requested"]["data"]["reason"]
