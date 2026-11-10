# Runbook: Slow checkout

**Owner:** shop team   **Severity:** warning   **Alert:** `alert-checkout-latency` (query `queries/02-p95-latency-5m.sql`)

## What this alert means
The p95 duration of `/checkout` is above 300 ms. One user in twenty waits that long or longer.

## First look
- Grafana Service Overview: p50 versus p95. A big gap is a slow tail; both rising is a shift of everything.
- Slowest traces (`day-17-observability/observability/queries/06-slowest-traces.sql`): which span holds the time?

## Likely causes
1. The `/price` call to `shop-backend` is slow (injected latency, a slow dependency).
2. CPU throttling: pod CPU pinned at its limit with no errors (Kubernetes / Infra dashboard).
3. Too little capacity for the traffic: HPA at its maximum, or a single replica.

## Mitigation
- `kubectl -n apps set env deploy/shop-backend INJECT_LATENCY_MS=0`
- Raise the CPU limit or scale: `kubectl -n apps scale deploy/shop-backend --replicas=2` (then fix in git)

## Verify recovery
p95 under 300 ms for 5 minutes; alert `resolved`.
