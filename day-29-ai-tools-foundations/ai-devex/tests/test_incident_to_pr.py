import json
import os

import pytest

pytest.importorskip("pytest_cov")
import pipeline  # noqa: E402


def events(run):
    return {e["stage"]: e for e in run.events}


def test_offline_end_to_end_stops_at_human_gate(tmp_path):
    run = pipeline.run_pipeline(str(tmp_path))
    e = events(run)
    assert e["baseline"]["tests_failed"] == 1
    assert e["measure"]["tests_failed"] == 0 and e["measure"]["first_pass_ci"] == 1
    assert e["review"]["decision"] == "approve"
    assert e["human-gate"]["status"] == "awaiting-human"
    assert json.load(open(tmp_path / "pr.json"))["head"] == "ai/fix-alert-4711"


def test_human_decision_feeds_agreement_metric(tmp_path):
    run = pipeline.run_pipeline(str(tmp_path), approve_as="dana")
    m = events(run)["metrics"]
    assert m["reviewer_human_agree"] is True and m["human_decision"] == "approve"


def test_original_sample_app_is_never_modified(tmp_path):
    src = os.path.join(pipeline.HERE, "sample-app", "pricing.py")
    before = open(src).read()
    pipeline.run_pipeline(str(tmp_path))
    assert open(src).read() == before and "/ 100" in before


def test_guardrail_stops_an_agent_that_edits_tests(tmp_path, monkeypatch):
    real = pipeline.fix_agent

    def sneaky(workdir, *a, **k):
        r = real(workdir, *a, **k)
        open(os.path.join(workdir, "tests", "test_pricing.py"), "w").write("def test_nothing():\n    assert True\n")
        return r

    monkeypatch.setattr(pipeline, "fix_agent", sneaky)
    run = pipeline.run_pipeline(str(tmp_path))
    last = run.events[-1]
    assert last["stage"] == "stopped" and "tests/test_pricing.py" in last["reason"] and "measure" not in events(run)


def test_budget_stops_the_run(tmp_path):
    run = pipeline.run_pipeline(str(tmp_path), budget=pipeline.Budget(max_calls=0))
    assert run.events[-1]["stage"] == "stopped" and "budget exceeded" in run.events[-1]["reason"]


def test_low_probability_triage_does_not_start_an_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "triage", lambda a, c: {"label": "not_code", "probability": 0.2, "reasons": []})
    run = pipeline.run_pipeline(str(tmp_path))
    assert run.events[-1]["stage"] == "stopped" and "fix" not in events(run)


def test_reviewer_must_be_a_different_model_and_vendor():
    with pytest.raises(ValueError):
        pipeline.reviewer("d", ["pricing.py"], {}, real_model="acme/big", author_model="acme/small")


def test_mock_reviewer_rejects_out_of_scope_or_failing_changes():
    assert pipeline.reviewer("d", ["pricing.py"], {"tests_failed": 0, "line_coverage_pct": 95})["decision"] == "approve"
    assert pipeline.reviewer("d", ["pricing.py", ".github/x"], {"tests_failed": 0, "line_coverage_pct": 95})["decision"] == "request_changes"
    assert pipeline.reviewer("d", ["pricing.py"], {"tests_failed": 1, "line_coverage_pct": 95})["decision"] == "request_changes"


def test_real_model_path_through_a_fake_gateway(tmp_path, fake_server, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", fake_server.url + "/v1")
    monkeypatch.setenv("FIX_MODEL", "acme/fixer")
    monkeypatch.setenv("REVIEW_MODEL", "other/reviewer")

    def answer(body):
        if body["model"] == "acme/fixer":
            return "```python\n" + pipeline.MOCK_FIX + "```"
        return "APPROVE\n- small diff"

    fake_server.answer = staticmethod(answer)
    run = pipeline.run_pipeline(str(tmp_path), real_models=True)
    e = events(run)
    assert e["review"]["reviewer"] == "other/reviewer" and e["review"]["decision"] == "approve"
    assert [s["body"]["model"] for s in fake_server.seen] == ["acme/fixer", "other/reviewer"]
    assert e["metrics"]["cost_usd"] == pytest.approx(0.0002)


def test_forgejo_pr_request_shape(fake_server):
    fake_server.answer = staticmethod(lambda b: {"html_url": "http://forge/o/r/pulls/1"})
    res = pipeline.forgejo_create_pr(fake_server.url, "tok", "o/r", "ai/x", "main", "title", "body")
    seen = fake_server.seen[0]
    assert res["html_url"].endswith("/pulls/1") and seen["path"] == "/api/v1/repos/o/r/pulls" and seen["auth"] == "token tok"
    assert seen["body"] == {"head": "ai/x", "base": "main", "title": "title", "body": "body"}
