"""Run the bridge:  python3 serve.py   (listens on 0.0.0.0:8080; needs fastapi and uvicorn: pip install fastapi uvicorn nats-py pyyaml)
Secrets come from the environment: BRIDGE_FORGEJO_SECRET and BRIDGE_TOKEN. Both are required; with either empty, that route answers 401 to everything."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn  # noqa: E402

import bridge  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(bridge.build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
