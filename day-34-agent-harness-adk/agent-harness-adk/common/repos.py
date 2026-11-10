"""Repository specs and a way to materialise one offline.

In production a worker would `git clone` from Forgejo. For an offline lab we stamp a repository with the
capstone's deterministic generator (capstone/gen/generate.py): real code, a thin test suite, a flaky test.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DOMAINS = ["billing", "booking", "catalog", "csv-importer", "inventory", "loyalty", "notifications", "payroll", "scheduler", "shipping", "ticketing", "url-shortener"]
HERE = Path(__file__).resolve().parent
GEN = Path(os.environ.get("GEN_SCRIPT", HERE.parent.parent.parent / "capstone" / "gen" / "generate.py"))


def make_specs(count: int, seed: int = 1000) -> list[dict]:
    return [{"name": f"{DOMAINS[i % len(DOMAINS)]}-py-{i + 1:03d}", "domain": DOMAINS[i % len(DOMAINS)], "seed": seed + i} for i in range(count)]


def materialise(spec: dict, dest: str) -> str:
    """Create the repository `spec` under `dest` and return its path."""
    if os.path.isdir(os.path.join(dest, spec["name"])):
        return os.path.join(dest, spec["name"])  # a retried Job finds the working tree its predecessor left on the volume
    keys = tempfile.mkdtemp()
    subprocess.run([sys.executable, str(GEN), "--out", dest, "--keys-dir", keys, "--csv", os.path.join(keys, "r.csv"), "--lang", "python",
                    "--domain", spec["domain"], "--name", spec["name"], "--seed", str(spec["seed"]), "--filler", "24"],
                   check=True, capture_output=True)
    return os.path.join(dest, spec["name"])


if __name__ == "__main__":
    print(json.dumps(make_specs(int(sys.argv[1]) if len(sys.argv) > 1 else 5)))
