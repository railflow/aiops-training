import pytest

from common import repo_tools as T
from common.faults import RateLimiter, RateLimited, parse
from common.mock_llm import decide


def test_baseline_coverage_is_measured(repo_dir):
    out = T.run_tests(repo_dir)
    assert 20 < out["coverage"] < 40
    assert out["uncovered_total"] > 0 and len(out["uncovered"]) <= T.MAX_UNCOVERED
    assert out["failed"] == 0  # the flaky test is filtered by one re-run


@pytest.mark.parametrize("path,content,message", [
    ("src/evil.py", "x = 1\n", "tests/test_"),
    ("tests/test_x.py", "import subprocess\n", "may not use"),
    ("tests/test_x.py", "def broken(:\n", "syntax error"),
    ("tests/test_x.py", "x = 1\n" * 10_000, "larger than"),
    ("tests/../../escape.py", "x = 1\n", "tests/test_"),
])
def test_write_test_file_refuses_unsafe_input(repo_dir, path, content, message):
    with pytest.raises(T.ToolError, match=message):
        T.write_test_file(repo_dir, path, content, [])


def test_branch_names_are_checked(repo_dir):
    with pytest.raises(T.ToolError, match="agent/"):
        T.git_commit(repo_dir, "main", "x")


def test_open_pr_is_idempotent(repo_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DIR", str(tmp_path / "forge"))
    T.write_test_file(repo_dir, "tests/test_one.py", "def test_ok():\n    assert True\n", ["x"])
    T.git_commit(repo_dir, "agent/coverage-x", "tests")
    first = T.open_pr(repo_dir, "agent/coverage-x", "t", "b")
    second = T.open_pr(repo_dir, "agent/coverage-x", "t", "b")
    assert first["url"] == second["url"] and second.get("deduplicated") is True


def test_chaos_parsing_and_rate_limiter():
    assert parse("a:stuck+rate_limit:2,b:oom@1", "a") == ["stuck", "rate_limit:2"]
    assert parse("a:stuck", "other") == []
    limiter = RateLimiter(["rate_limit:2"])
    for _ in range(2):
        with pytest.raises(RateLimited):
            limiter.check()
    limiter.check()


def test_mock_policy_is_a_pure_function_of_history():
    history = [{"role": "user", "text": "Raise test coverage of repo=r to 80%."}]
    assert decide("all", history, 80.0).calls[0].name == "run_tests"
    assert decide("all", history, 80.0).calls[0].name == "run_tests"
