# Runbook: Synthetic traffic (k6) is not arriving

**Owner:** shop team   **Severity:** info   **Alert:** `alert-synthetic-traffic`

## What this alert means
The steady k6 load that keeps the error-rate and latency alerts meaningful has stopped. Those alerts report 0 when there are fewer than 20 requests, so they are blind until the load is back.

## Mitigation
Local: restart the loop (`k6 run ... loop.js`) or the in-cluster Deployment: `kubectl -n loadgen get pods`. Check the user-agent attribute name if the query returns 0 while k6 clearly runs (see the comment in `queries/08-synthetic-traffic-flowing.sql`).
