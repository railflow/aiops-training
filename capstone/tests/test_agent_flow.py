"""End to end, with a STUB `claude`: run-agent.sh clones, runs the 'agent', checks, pushes a branch; evaluate.sh measures it. No model, no network, no cluster."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
G = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]


def last_result(out, err=""):
    assert "RESULT " in out, out + err
    return json.loads(next(l for l in reversed(out.splitlines()) if l.startswith("RESULT "))[7:])


@pytest.fixture
def world(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / "repos"), "--lang", "python", "--domain", "billing", "--name", "billing-py-001"], check=True, capture_output=True)
    bare = tmp_path / "bare" / "capstone" / "billing-py-001.git"
    bare.parent.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "push", "-q", str(bare), "main"], cwd=tmp_path / "repos" / "billing-py-001", check=True)
    stub = tmp_path / "bin"
    stub.mkdir()
    return tmp_path, stub


def env(tmp, stub):
    path = os.pathsep.join([str(stub), str(Path(sys.executable).parent), str(ROOT.parent / "scripts"), os.environ["PATH"]])
    return {**os.environ, "PATH": path, "FORGEJO_URL": f"file://{tmp / 'bare'}", "FORGEJO_TOKEN": "x", "REPO": "capstone/billing-py-001", "AGENT_RUN_ID": "r1",
            "AGENT_DIR": str(ROOT / "agent"), "PROMPTS_DIR": str(ROOT / "agent" / "prompts"), "OPEN_PR": "0", "HOME": str(tmp / "home"), "MEASURE_SHIP": "0",
            "MEASURE_PY": str(ROOT / "measure" / "measure.py"), "REPORT_DIR": str(tmp / "reports")}


def stub_claude(stub, body):
    f = stub / "claude"
    f.write_text("#!/usr/bin/env bash\nif [ \"$1\" = --version ]; then echo '0.0-stub'; exit 0; fi\n" + body + "\necho '{\"total_cost_usd\": 0.12, \"num_turns\": 3, \"usage\": {\"input_tokens\": 100, \"output_tokens\": 20}}'\n")
    f.chmod(0o755)


def run(cmd, e, cwd):
    return subprocess.run(["bash", str(ROOT / "agent" / cmd)], env=e, cwd=cwd, capture_output=True, text=True)


GOOD = r"""cat > tests/test_extra.py <<'PY'
from invoice_service.core import create_invoice, describe_invoice

def test_describe():
    assert describe_invoice(create_invoice('acme', 5)) == 'acme (5)'
PY"""


def test_good_agent_run_then_trusted_evaluation(world):
    tmp, stub = world
    stub_claude(stub, GOOD)
    e = {**env(tmp, stub), "WORK_DIR": str(tmp / "agentwork")}
    r = run("run-agent.sh", e, tmp)
    res = last_result(r.stdout, r.stderr)
    assert res["outcome"] == "pushed" and res["commits"] == 1 and res["cost_usd"] == 0.12 and res["tool_versions"]["claude"] == "0.0-stub", r.stdout + r.stderr
    assert res["branch"] == "ai/coverage-r1"
    branches = subprocess.run(["git", "--git-dir", str(tmp / "bare" / "capstone" / "billing-py-001.git"), "branch", "--list"], capture_output=True, text=True).stdout
    assert "ai/coverage-r1" in branches
    ev = run("evaluate.sh", {**e, "WORK_DIR": str(tmp / "evalwork"), "BRANCH": res["branch"], "PREV_COVERAGE": "0"}, tmp)
    out = last_result(ev.stdout)
    assert out["ok"] is True, ev.stdout + ev.stderr
    assert out["measurement"]["repo"] == "billing-py-001" and out["measurement"]["test_count"] >= 10 and out["coverage"] > 0


def test_agent_that_deletes_tests_is_not_pushed(world):
    tmp, stub = world
    stub_claude(stub, "rm tests/test_core.py")
    e = {**env(tmp, stub), "WORK_DIR": str(tmp / "agentwork")}
    res = last_result(run("run-agent.sh", e, tmp).stdout)
    assert res["outcome"] == "integrity-failed"
    branches = subprocess.run(["git", "--git-dir", str(tmp / "bare" / "capstone" / "billing-py-001.git"), "branch", "--list"], capture_output=True, text=True).stdout
    assert "ai/" not in branches


def test_evaluate_refuses_a_coverage_drop(world):
    tmp, stub = world
    stub_claude(stub, GOOD)
    e = {**env(tmp, stub), "WORK_DIR": str(tmp / "agentwork")}
    res = last_result(run("run-agent.sh", e, tmp).stdout)
    ev = last_result(run("evaluate.sh", {**e, "WORK_DIR": str(tmp / "evalwork"), "BRANCH": res["branch"], "PREV_COVERAGE": "99"}, tmp).stdout)
    assert ev["ok"] is False and any("coverage dropped" in x for x in ev["reasons"])
