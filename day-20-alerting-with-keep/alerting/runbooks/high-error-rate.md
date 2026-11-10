# Runbook: High error rate on shop-frontend

**Owner:** shop team   **Severity:** critical   **Alert:** `alert-error-rate` (query `queries/01-error-rate-5m.sql`)

## What this alert means
More than 5% of user requests to `shop-frontend` failed over the last 5 minutes. Customers see errors when they check out.

## First look (5 minutes)
- Grafana: Service Overview (RED), then Logs & Traces.
- Which endpoint? Run `day-17-observability/observability/queries/08-failed-spans.sql`.
- Open one failed trace. Which span has the error: `shop-frontend` itself or the child call to `shop-backend`?

## Likely causes
1. A deploy or config change in the last hour: `kubectl -n apps rollout history deploy/shop-backend` and `deploy/shop-frontend`.
2. `shop-backend` failing (`/price`): check its error logs for `injected failure` or a real exception.
3. Injected faults left on from a drill: `kubectl -n apps get deploy shop-backend -o jsonpath='{.spec.template.spec.containers[0].env}'`.
4. Resource limits: restarts or memory near limit (see the pod-restarts and oomkilled runbooks).

## Mitigation
- Turn faults off: `kubectl -n apps set env deploy/shop-backend INJECT_ERROR_RATE=0 INJECT_LATENCY_MS=0`
- Roll back: `kubectl -n apps rollout undo deploy/shop-backend`

## Verify recovery
Error rate under 5% on the dashboard and the alert shows `resolved` in Keep within about 5 to 6 minutes (the query looks back 5 minutes).

## Who to call
Primary on-call, then secondary after 5 minutes unacknowledged.
