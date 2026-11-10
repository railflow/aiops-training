import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from fake_forgejo import Fake  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def make(tmp_path, n=3):
    subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / "repos"), "--csv", str(tmp_path / "repos.csv"), "--count", str(n), "--seed", "3"],
                   check=True, capture_output=True)
    return tmp_path / "repos.csv"


def env(fake, bare):
    return {**os.environ, "FORGEJO_URL": fake.url, "FORGEJO_GIT_URL": f"file://{bare}", "FORGEJO_TOKEN": "t0ken-for-tests", "WEBHOOK_SECRET": "shh"}


@pytest.fixture
def fake(tmp_path):
    f = Fake(tmp_path / "bare")
    yield f
    f.stop()


def check_state(fake, bare, n, hook):
    assert len(fake.repos) == n
    for (org, name), r in fake.repos.items():
        assert org == "capstone" and {"bug", "ai-found", "security"} <= {l["name"] for l in r["labels"]} and len(r["labels"]) == 9
        assert "capstone" in r["topics"] and r["settings"]["has_projects"] is True
        assert [h["config"]["url"] for h in r["hooks"]] == [hook]       # exactly one hook, even after a re-run
        head = subprocess.run(["git", "--git-dir", str(bare / "capstone" / f"{name}.git"), "log", "--oneline", "main"], capture_output=True, text=True).stdout.splitlines()
        assert head[0].endswith("Add golden-path CI workflow") and len(head) == 4
    assert fake.tokens == {"token t0ken-for-tests"}


def test_python_script_is_idempotent(tmp_path, fake):
    csv = make(tmp_path)
    cmd = [sys.executable, str(ROOT / "forgejo" / "push_repos.py"), "--csv", str(csv), "--parallel", "3", "--webhook-url", "http://hook.test/forgejo"]
    for run in (1, 2):
        r = subprocess.run(cmd, env=env(fake, tmp_path / "bare"), capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "summary: 3 ok, 0 failed" in r.stdout
        assert ("created" in r.stdout) == (run == 1) and ("exists" in r.stdout) == (run == 2)
    check_state(fake, tmp_path / "bare", 3, "http://hook.test/forgejo")
    for repo in (tmp_path / "repos").iterdir():                          # the token must not leak into the local repos
        assert "t0ken-for-tests" not in (repo / ".git" / "config").read_text()


def test_bash_script_is_idempotent_and_retries_429(tmp_path):
    fake = Fake(tmp_path / "bare", fail_once_429=True)
    try:
        csv = make(tmp_path)
        e = {**env(fake, tmp_path / "bare"), "WEBHOOK_URL": "http://hook.test/forgejo"}
        for run in (1, 2):
            r = subprocess.run(["bash", str(ROOT / "forgejo" / "push_repos.sh"), str(csv), "capstone", "3"], env=e, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            assert "summary: 3 ok, 0 failed" in r.stdout
        check_state(fake, tmp_path / "bare", 3, "http://hook.test/forgejo")
    finally:
        fake.stop()


def test_cleanup_dry_run_and_delete(tmp_path, fake):
    csv = make(tmp_path, 2)
    e = env(fake, tmp_path / "bare")
    subprocess.run([sys.executable, str(ROOT / "forgejo" / "push_repos.py"), "--csv", str(csv)], env=e, check=True, capture_output=True)
    dry = subprocess.run(["bash", str(ROOT / "forgejo" / "cleanup.sh"), str(csv), "capstone"], env={**e, "DRY_RUN": "1"}, capture_output=True, text=True)
    assert dry.stdout.count("would delete") == 2 and len(fake.repos) == 2
    r = subprocess.run(["bash", str(ROOT / "forgejo" / "cleanup.sh"), str(csv), "capstone", "--delete-org"], env={**e, "DELAY": "0"}, input="capstone\n", capture_output=True, text=True)
    assert len(fake.repos) == 0 and "204" in r.stdout
    wrong = subprocess.run(["bash", str(ROOT / "forgejo" / "cleanup.sh"), str(csv), "capstone"], env=e, input="nope\n", capture_output=True, text=True)
    assert wrong.returncode == 1


def test_file_issue_dedupes_labels_and_caps(tmp_path, fake):
    csv = make(tmp_path, 1)
    e = env(fake, tmp_path / "bare")
    subprocess.run([sys.executable, str(ROOT / "forgejo" / "push_repos.py"), "--csv", str(csv)], env=e, check=True, capture_output=True)
    name = next(n for (_, n) in fake.repos)
    base = {**e, "REPO": f"capstone/{name}", "AGENT_RUN_ID": "run-1", "ISSUE_COUNTER_FILE": str(tmp_path / "count"), "MAX_ISSUES": "2"}
    cmd = [sys.executable, str(ROOT / "agent" / "bin" / "file_issue.py"), "--severity", "high", "--body", "expected 3, got 2", "--file", "a.py", "--line", "4", "--test", "test_x"]
    r1 = subprocess.run([*cmd, "--title", "Paginate drops the last item"], env=base, capture_output=True, text=True)
    r2 = subprocess.run([*cmd, "--title", "paginate DROPS the last item!"], env=base, capture_output=True, text=True)    # same after normalising
    r3 = subprocess.run([*cmd, "--title", "A different bug"], env=base, capture_output=True, text=True)
    r4 = subprocess.run([*cmd, "--title", "Third bug"], env=base, capture_output=True, text=True)
    assert r1.stdout.startswith("FILED #1") and r2.stdout.startswith("DUPLICATE #1") and r3.stdout.startswith("FILED #2")
    assert r4.returncode == 3                                                                                          # per-run cap
    issues = fake.repos[("capstone", name)]["issues"]
    assert len(issues) == 2 and "capstone-fingerprint:" in issues[0]["body"] and "file: a.py; line: 4" in issues[0]["body"]
    assert len(issues[0]["labels"]) == 2                                                                               # bug + ai-found
