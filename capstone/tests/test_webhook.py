import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webhook"))
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
import app as hook  # noqa: E402

SECRET = "test-secret"
REPO = {"full_name": "capstone/billing-py-001", "default_branch": "main"}


@pytest.fixture
def client():
    d = hook.RecordingDispatcher()
    return TestClient(hook.create_app(SECRET, d)), d


def post(c, event, payload, secret=SECRET, header="x-forgejo-signature", delivery="d1", path="/forgejo"):
    body = json.dumps(payload).encode()
    sig = hook.sign(secret, body)
    h = {header: ("sha256=" + sig) if header == "x-hub-signature-256" else sig, "x-forgejo-event": event, "x-forgejo-delivery": delivery, "content-type": "application/json"}
    return c.post(path, content=body, headers=h)


def test_refuses_to_start_without_a_secret():
    with pytest.raises(RuntimeError):
        hook.create_app("", hook.RecordingDispatcher())


def test_bad_signature_is_rejected_and_nothing_starts(client):
    c, d = client
    assert post(c, "push", {"repository": REPO, "ref": "refs/heads/main", "after": "a" * 40}, secret="wrong").status_code == 401
    assert c.post("/forgejo", content=b"{}").status_code == 401
    assert d.started == [] and d.signalled == []


@pytest.mark.parametrize("header", ["x-forgejo-signature", "x-gitea-signature", "x-hub-signature-256"])
def test_all_three_signature_headers_work(client, header):
    c, d = client
    r = post(c, "push", {"repository": REPO, "ref": "refs/heads/main", "after": "b" * 40}, header=header)
    assert r.status_code == 200 and r.json()["status"] == "started"
    assert d.started[0][0] == "MeasureRepoWorkflow" and d.started[0][1] == "measure-capstone-billing-py-001-" + "b" * 12


def test_push_to_a_feature_branch_or_branch_delete_is_ignored(client):
    c, d = client
    assert post(c, "push", {"repository": REPO, "ref": "refs/heads/ai/coverage-1", "after": "c" * 40}).json()["status"] == "ignored"
    assert post(c, "push", {"repository": REPO, "ref": "refs/heads/main", "after": "0" * 40}, delivery="d2").json()["status"] == "ignored"
    assert d.started == []


def test_ai_fix_label_starts_a_fix_workflow(client):
    c, d = client
    p = {"repository": REPO, "action": "label_updated", "issue": {"number": 7, "labels": [{"name": "bug"}, {"name": "ai-fix"}]}}
    assert post(c, "issues", p).json()["status"] == "started"
    assert d.started[0] == ("FixIssueWorkflow", "fix-capstone-billing-py-001-7", {"repo": "capstone/billing-py-001", "issue_number": 7})
    p["issue"]["labels"] = [{"name": "bug"}]
    assert post(c, "issues", p, delivery="d2").json()["status"] == "ignored"


def test_approval_and_ci_finished_signal_the_improve_workflow(client):
    c, d = client
    post(c, "pull_request_review_approved", {"repository": REPO, "pull_request": {"number": 3}, "sender": {"login": "alice"}})
    assert d.signalled[0] == ("improve-capstone-billing-py-001", "human_approval", {"pr": 3, "reviewer": "alice"})
    assert post(c, "", {"repo": "capstone/billing-py-001", "run_id": "9", "sha": "abc", "status": "success"}, path="/ci-finished", delivery="").status_code == 200
    assert d.signalled[1] == ("improve-capstone-billing-py-001", "ci_finished", {"run_id": "9", "sha": "abc", "status": "success"})


def test_redelivery_is_dropped(client):
    c, d = client
    p = {"repository": REPO, "ref": "refs/heads/main", "after": "d" * 40}
    assert post(c, "push", p, delivery="same").json()["status"] == "started"
    assert post(c, "push", p, delivery="same").json()["status"] == "duplicate-delivery"
    assert len(d.started) == 1
