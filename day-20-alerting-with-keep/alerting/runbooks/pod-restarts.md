# Runbook: Containers restarting

**Owner:** shop team   **Severity:** warning   **Alert:** `alert-pod-restarts`

## First look
- `kubectl -n apps get pods` (RESTARTS column) and `kubectl -n apps describe pod <pod>` (Last State, Reason, Exit Code).
- `kubectl -n apps logs <pod> --previous` shows the crashed container's last output.

## Likely causes
Exit code 137 and `OOMKilled`: memory limit (see the oomkilled runbook). Exit code 1: application crash or bad config. Liveness probe failures: the probe is too strict or the app is stuck.

## Mitigation
Fix the cause in git; as a stop-gap raise the limit or roll back: `kubectl -n apps rollout undo deploy/<name>`.
