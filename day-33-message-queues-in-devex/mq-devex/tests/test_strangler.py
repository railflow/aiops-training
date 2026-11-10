"""Lab 4: the strangler facade. Flip the flag at runtime and watch traffic move, with no redeploy and no change to the caller."""
import asyncio
import json
import time

import pytest
from nats.js.api import KeyValueConfig

import adapters
import compare
import devbus
import facade


@pytest.mark.parametrize("flag,repo,want", [
    ("legacy", "a", [("legacy", False)]),
    ("new", "a", [("new", False)]),
    ("shadow", "a", [("legacy", False), ("new", True)]),
    ("canary:0", "a", [("legacy", False)]),
    ("canary:100", "a", [("new", False)]),
])
def test_pick(flag, repo, want):
    assert facade.pick(flag, repo) == want


def test_canary_is_stable_per_repo_and_roughly_proportional():
    picks = [facade.pick("canary:30", f"repo-{i}")[0][0] for i in range(400)]
    assert 0.2 < picks.count("new") / 400 < 0.4
    assert facade.pick("canary:30", "repo-7") == facade.pick("canary:30", "repo-7")


def test_unknown_flag_is_a_permanent_error():
    with pytest.raises(devbus.PermanentError):
        facade.pick("banana", "a")


def test_legacy_output_parser():
    assert adapters.parse_legacy("TESTS=42\nRESULT=SUCCESS\n", 0)["passed"] is True
    assert adapters.parse_legacy("RESULT=FAILURE\n", 1)["passed"] is False
    assert adapters.parse_legacy("garbage", 0)["passed"] is False


async def read(js, subj):
    sub = await js.pull_subscribe(subj, stream=devbus.STREAM)
    out = []
    while True:
        try:
            msgs = await sub.fetch(50, timeout=0.5)
        except Exception:
            break
        for m in msgs:
            out.append(json.loads(m.data))
            await m.ack()
    await sub.unsubscribe()
    return out


async def request(js, repo, sha, fail=False):
    ev = devbus.new_event("ci.requested", {"repo": repo, "sha": sha, "flags": {"fail": fail}}, source="test")
    await devbus.publish(js, "ci.requested", ev)
    return ev


def test_flag_flip_moves_traffic_and_shadow_catches_a_bug(nats_url, state_dir, monkeypatch):
    monkeypatch.setenv("LEGACY_SECONDS", "0.05")
    monkeypatch.setenv("NEW_SECONDS", "0.05")

    async def run():
        nc, js = await devbus.connect(nats_url)
        kv = await js.create_key_value(config=KeyValueConfig(bucket="flags"))
        stop = asyncio.Event()
        kw = dict(js=js, state_dir=state_dir, stop=stop, ack_wait=5)
        tasks = [asyncio.create_task(devbus.run_worker(n, f, h, **kw)) for n, f, h in [
            ("ci-facade", "ci.requested", facade.handle), ("adapter-legacy", "ci.run.legacy", adapters.legacy_handle),
            ("adapter-new", "ci.run.new", adapters.new_handle), ("ci-compare", "ci.completed", compare.handle)]]

        async def wait_for(n):
            end = time.time() + 15
            while time.time() < end:
                done = await read(js, "ci.completed")
                if len(done) >= n:
                    return done
                await asyncio.sleep(0.2)
            raise AssertionError("timeout")

        await request(js, "orders-api", "s1")                       # no flag yet -> legacy
        first = await wait_for(1)
        await kv.put("ci-runner", b"new")
        await request(js, "orders-api", "s2")
        second = await wait_for(2)
        await kv.put("ci-runner", b"shadow")
        monkeypatch.setenv("NEW_BUG", "1")                          # the replacement has a bug that only shadow mode will reveal
        await request(js, "orders-api", "s3")
        third = await wait_for(4)
        end = time.time() + 10
        cmp_ = []
        while not cmp_ and time.time() < end:
            cmp_ = await read(js, "ci.compare.result")
            await asyncio.sleep(0.2)
        stop.set()
        await asyncio.gather(*tasks)
        await nc.close()
        return first, second, third, cmp_

    first, second, third, cmp_ = asyncio.run(run())
    assert [e["data"]["impl"] for e in first] == ["legacy"]
    assert sorted(e["data"]["impl"] for e in second) == ["legacy", "new"]
    shadow_run = [e for e in third if e["data"]["sha"] == "s3"]
    assert {(e["data"]["impl"], e["data"]["shadow"]) for e in shadow_run} == {("legacy", False), ("new", True)}
    assert len(cmp_) == 1 and cmp_[0]["data"]["agree"] is False
    assert cmp_[0]["data"]["legacy_passed"] is True and cmp_[0]["data"]["new_passed"] is False
