import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import repos  # noqa: E402


@pytest.fixture
def spec():
    return repos.make_specs(1)[0]


@pytest.fixture
def repo_dir(tmp_path, spec):
    return repos.materialise(spec, str(tmp_path / "repos"))


@pytest.fixture
def worker_env(tmp_path, spec):
    """Environment for running a worker as a subprocess, exactly as a Job would."""
    return {**os.environ, "PYTHONPATH": str(ROOT), "REPO_NAME": spec["name"], "REPO_DOMAIN": spec["domain"], "REPO_SEED": str(spec["seed"]),
            "WORK_DIR": str(tmp_path / "work"), "STATE_DIR": str(tmp_path / "state"), "FORGE_DIR": str(tmp_path / "forge")}


def run_worker(module: str, env: dict, **extra) -> tuple[int, dict | None, str]:
    p = subprocess.run([sys.executable, "-m", module], env={**env, **{k: str(v) for k, v in extra.items()}}, capture_output=True, text=True, cwd=ROOT, timeout=240)
    lines = [ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")]
    return p.returncode, json.loads(lines[-1][7:]) if lines else None, p.stderr


@pytest.fixture
def fake_kube(tmp_path, monkeypatch):
    state = tmp_path / "kube"
    monkeypatch.setenv("FAKE_KUBE_STATE", str(state))
    monkeypatch.setenv("KUBECTL", f"{sys.executable} {ROOT / 'tests' / 'fake_kubectl.py'}")
    monkeypatch.delenv("FAKE_THROTTLE", raising=False)
    return state


def kube_db(state: Path) -> dict:
    return json.loads((state / "db.json").read_text())
