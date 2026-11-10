"""Load a real provider by file path.

The provider folders are named `modal/` and `daytona/`, the same as the SDK packages they wrap, so they are never
put on the import path as packages; this loads `<folder>/provider.py` under a private module name instead.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_PROVIDERS = {"modal": ("ModalProvider", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"), "daytona": ("DaytonaProvider", "DAYTONA_API_KEY")}


def load_provider_module(folder: str):
    path = ROOT / folder / "provider.py"
    name = f"sandbox_provider_{folder}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(folder: str) -> int:
    import os

    from common.run_task import load_task, run_task

    cls_name, *needs = PY_PROVIDERS[folder]
    if os.environ.get("SANDBOX_ALLOW_REAL") != "1":
        print("Real runs create billable sandboxes with whatever credentials are in your environment or profile.\n"
              "Set SANDBOX_ALLOW_REAL=1 to confirm. The offline default path is: python run_mock.py")
        return 2
    missing = [n for n in needs if not os.environ.get(n)]
    if missing and not (folder == "modal" and (Path.home() / ".modal.toml").exists()):
        print(f"Set {' and '.join(missing)}. Names only; put values in your shell, never in the repo.")
        return 2
    provider = getattr(load_provider_module(folder), cls_name)()
    result = run_task(provider, load_task())
    print(json.dumps({"provider": result.provider, "sandbox": result.sandbox_id, "coverage_before": result.coverage_before,
                      "coverage_after": result.coverage_after, "diff_preview": result.diff.splitlines()[:12], "events": result.events}, indent=2))
    return 0
