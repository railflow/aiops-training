"""The default path: run the common task on the offline mock provider. No network, no account, no cost.

python run_mock.py            # inside a sandbox (isolated mock)
python run_mock.py --bare     # the same task on a bare-host model, for contrast
python run_mock.py --injected # the agent obeys the injected README line; compare with --bare
"""
from __future__ import annotations

import argparse
import json

from common.fake_agent import FakeAgent, GullibleAgent
from common.run_task import load_task, run_task
from mock.provider import MockProvider


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bare", action="store_true", help="model a bare host instead of a sandbox")
    ap.add_argument("--injected", action="store_true", help="use the agent that obeys instructions found in the README")
    args = ap.parse_args()
    agent = GullibleAgent() if args.injected else FakeAgent()
    provider = MockProvider(isolated=not args.bare)
    result = run_task(provider, load_task(), agent=agent)
    obeyed = [{"command": c, "exit_code": r.exit_code, "output": (r.stderr or r.stdout).strip()[:160]}
              for c, r in zip(getattr(agent, "obeyed", []), getattr(agent, "results", []))]
    print(json.dumps({
        "provider": result.provider,
        "coverage_before": result.coverage_before,
        "coverage_after": result.coverage_after,
        "steps": [e["step"] for e in result.events],
        "agent": result.agent,
        "injected_commands_obeyed": obeyed,
        "diff_preview": result.diff.splitlines()[:8],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
