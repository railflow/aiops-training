import json
import os

import run_evals as ev

TASKS = json.load(open(os.path.join(os.path.dirname(__file__), "..", "evals", "tasks.json")))


def test_five_tasks_with_unique_ids():
    assert len(TASKS) == 5 and len({t["id"] for t in TASKS}) == 5


def test_careful_mock_passes_everything_and_sloppy_fails_everything():
    rows = ev.run(["mock:careful", "mock:sloppy"], TASKS)
    s = ev.summarise(rows)
    assert s["mock:careful"]["pass_rate"] == 1.0
    assert s["mock:sloppy"]["pass_rate"] == 0.0


def test_each_check_rejects_a_near_miss():
    by = {t["id"]: t["check"] for t in TASKS}
    assert not ev.score('{"package": "orders-api", "version": "3.14"}', by["extract-version"])
    assert ev.score('Here you go: {"package": "orders-api", "version": "3.14.2"}', by["extract-version"])
    assert not ev.score("ERROR: bad", by["classify-log-severity"])
    assert not ev.score("```python\ndef last_n(items, n):\n    return items[-n:]\n```", by["fix-off-by-one"])
    assert not ev.score("x" * 10 + "hunter2-FAKE-0000", by["do-not-leak-secret"])
    assert not ev.score("Fix the retry bug in the webhook sender and also do a lot of other unrelated cleanup work today", by["commit-message-format"])
    assert not ev.score("Add retry.\n\nbody", by["commit-message-format"])
    assert not ev.score("Add retry\nbody directly", by["commit-message-format"])


def test_infinite_loop_in_generated_code_times_out_as_a_failure(monkeypatch):
    import subprocess
    real = subprocess.run
    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **k: real(*a, **{**k, "timeout": 1}))
    bad = "```python\ndef last_n(items, n):\n    while True: pass\n```"
    assert not ev.score(bad, {"type": "code_tests", "function": "last_n", "cases": [[[[1], 1], [1]]]})


def test_gateway_path_via_fake_server(fake_server, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", fake_server.url + "/v1")
    fake_server.answer = staticmethod(lambda body: "ERROR")
    rows = ev.run(["vendor/model-x"], [t for t in TASKS if t["id"] == "classify-log-severity"])
    assert rows[0]["pass"] and rows[0]["cost"] == 0.0001 and rows[0]["in"] == 7
