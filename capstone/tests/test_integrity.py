import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
import integrity_check as ti  # noqa: E402,F401

G = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]


def run(cwd, *a):
    subprocess.run([*G, *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    run(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "svc.py").write_text("def f(x):\n    return x + 1\n")
    (tmp_path / "tests" / "test_svc.py").write_text("from svc import f\n\ndef test_f():\n    assert f(1) == 2\n\ndef test_g():\n    assert f(2) == 3\n    assert f(3) == 4\n")
    run(tmp_path, "add", "."); run(tmp_path, "commit", "-q", "-m", "base")
    run(tmp_path, "branch", "base"); run(tmp_path, "checkout", "-q", "-b", "ai/work")
    return tmp_path


def commit(repo, msg="change"):
    run(repo, "add", "."); run(repo, "commit", "-q", "-m", msg)


def rules(repo, **kw):
    return {v["rule"] for v in ti.check(str(repo), "base", **kw)}


def test_adding_real_tests_is_fine(repo):
    (repo / "tests" / "test_more.py").write_text("from svc import f\n\ndef test_h():\n    assert f(0) == 1\n")
    commit(repo)
    assert rules(repo, no_src_changes=True) == set()


def test_deleting_a_test_file_is_flagged(repo):
    (repo / "tests" / "test_svc.py").unlink(); commit(repo)
    assert rules(repo) == {"deleted-test-file"}


def test_removing_a_test_and_an_assertion_is_flagged(repo):
    (repo / "tests" / "test_svc.py").write_text("from svc import f\n\ndef test_f():\n    assert f(1) == 2\n"); commit(repo)
    assert rules(repo) == {"fewer-tests", "fewer-assertions"}


def test_weakening_an_assertion_to_a_tautology_is_flagged(repo):
    (repo / "tests" / "test_svc.py").write_text("from svc import f\n\ndef test_f():\n    assert True\n\ndef test_g():\n    assert f(2) == 3\n    assert f(3) == 4\n"); commit(repo)
    assert "trivial-assertion" in rules(repo)


def test_skip_needs_an_issue_reference(repo):
    t = repo / "tests" / "test_svc.py"
    t.write_text(t.read_text() + "\nimport pytest\n\n@pytest.mark.skip(reason='broken')\ndef test_bad():\n    assert f(0) == 5\n"); commit(repo)
    assert "skip-without-issue" in rules(repo)
    t.write_text(t.read_text().replace("reason='broken'", "reason='bug #12: f(0) is wrong'")); commit(repo, "ref")
    assert "skip-without-issue" not in rules(repo)


def test_production_change_is_flagged_only_when_forbidden(repo):
    (repo / "svc.py").write_text("def f(x):\n    return x + 2\n"); commit(repo)
    assert rules(repo) == set()
    assert rules(repo, no_src_changes=True) == {"src-changed"}
