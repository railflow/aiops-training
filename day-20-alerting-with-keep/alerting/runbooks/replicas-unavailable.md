# Runbook: Fewer replicas available than desired

**Owner:** shop team (platform team if nodes are involved)   **Severity:** high   **Alert:** `alert-replicas-unavailable`

## First look
- `kubectl -n apps get deploy,pods` and `kubectl -n apps describe deploy <name>`.
- Pods Pending: `kubectl describe pod` (Insufficient CPU or memory, unbound PVC, image pull error).
- Readiness failing: the `/healthz` or `/readyz` endpoint, then the app logs.
- During a normal rollout this alert can fire briefly; if it clears within a few minutes, no action is needed.

## Mitigation
Roll back the change, or fix scheduling (requests too large for the node), or restore the dependency that readiness checks.
