import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py"))
import lab_common as lab  # noqa: E402
import crash_lab as cl  # noqa: E402


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for k in ("LAB_DIE_AT", "LAB_NO_IDEMPOTENCY"):
        monkeypatch.delenv(k, raising=False)


def test_pause_for_confirmation_then_approve_in_a_new_process():
    cl.parked()


def test_crash_inside_a_tool_then_resume():
    cl.step_crash()


def test_a_denied_confirmation_opens_no_pull_request(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_DIR", str(tmp_path))
    cl.process("start", "billing-003", str(tmp_path))
    _, status = cl.process("deny", "billing-003", str(tmp_path))
    assert status["final"] == "stopped: pull request not approved"
    assert lab.pull_requests() == []
