"""The first-draft loop on a good day and on each bad day. These tests document the failures Day 34 starts from."""
import subprocess
import sys

import pytest

from common import faults as F
from common.repos import make_specs
from hand_rolled.llm import MockLLM
from hand_rolled.naive_loop import naive_run
from tests.conftest import ROOT


def run(repo_dir, spec, fault, monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_DIR", str(tmp_path / "forge"))
    f = F.parse(f"{spec['name']}:{fault}" if fault else "", spec["name"])
    return naive_run(repo_dir, MockLLM("all", 80.0, F.model_faults(f), F.RateLimiter(f)), spec["name"])


def test_good_day(repo_dir, spec, monkeypatch, tmp_path):
    assert run(repo_dir, spec, "", monkeypatch, tmp_path).startswith("done")


@pytest.mark.parametrize("fault,error", [("bad_tool", KeyError), ("malformed_args", TypeError), ("rate_limit:1", F.RateLimited)])
def test_these_bad_days_crash_it(repo_dir, spec, monkeypatch, tmp_path, fault, error):
    with pytest.raises(error):
        run(repo_dir, spec, fault, monkeypatch, tmp_path)


def test_a_malformed_reply_looks_like_success(repo_dir, spec, monkeypatch, tmp_path):
    assert run(repo_dir, spec, "malformed_json", monkeypatch, tmp_path) is None  # no calls and no text: "finished", nothing done


def test_a_stuck_model_never_returns(tmp_path, spec):
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "FORGE_DIR": str(tmp_path)}
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([sys.executable, "-m", "hand_rolled.naive_loop", f"{spec['name']}:stuck"], env=env, cwd=ROOT, capture_output=True, timeout=12)
