# Runbook: No telemetry from shop-frontend (dead man's switch)

**Owner:** shop team and platform team   **Severity:** critical   **Alert:** `alert-no-traffic`

## What this alert means
No spans and no logs reached ClickHouse for 5 minutes. Either the service is down, nobody is calling it, or the telemetry pipeline is broken. Silence is a failure too.

## First look
1. Is the app alive? `kubectl -n apps get pods` and `curl -i http://shop.localhost:8080/healthz`.
2. Is the pipeline alive? `kubectl -n observability get pods` (collector gateway, agent, ClickHouse).
3. Is the load running? A quiet system with no k6 loop is normal locally; check the synthetic-traffic alert.

## Mitigation
- App down: `kubectl -n apps describe pod ...`, roll back the last change.
- Collector down: `kubectl -n observability logs deploy/otel-gateway --tail=50`, restart it.
- ClickHouse down: `kubectl -n observability get pod clickhouse-0` and see the PVC; this alert cannot fire if Keep cannot query ClickHouse, which is why Gatus (Day 21) checks from outside.

## Who to call
Platform team if the observability namespace is unhealthy; shop team otherwise.
