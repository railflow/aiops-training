# workflows/: orchestration

`flow_workflows.py` (deterministic), `flow_activities.py` (side effects), `flow_runners.py` (kubectl or fake), `forge.py` (Forgejo REST), `worker.py`, `start.py` (start, pause, resume, status, kill).
Run the tests: `pytest ../tests/test_workflows.py ../tests/test_activities.py` (the first run downloads the Temporal test server).
