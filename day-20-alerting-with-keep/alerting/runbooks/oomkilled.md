# Runbook: Probable OOMKill / memory near limit

**Owner:** shop team   **Severity:** high (restart near limit), warning (memory above 90%)   **Alerts:** `alert-oom-suspects`, `alert-memory-near-limit`

## First look
- `kubectl -n apps describe pod <pod>`: look for `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`.
- Kubernetes / Infra dashboard: memory versus limit per pod, restarts.
- Is memory growing steadily (a leak) or does it jump with a request type (a large allocation)?

## Mitigation
- Raise the memory limit and request in the manifest (git commit, not `kubectl edit`).
- Fix the leak or the unbounded allocation; add a test.
- Note: if the killed process is a gunicorn worker rather than PID 1, the container may not restart; read the logs for `Worker ... was sent SIGKILL`.
