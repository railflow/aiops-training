---
title: Roll back a deploy
description: A runbook-style how-to guide. Short, for someone who already knows the basics.
---

Use this when a new release is failing its health check and you want the previous version back.

## Steps

1. **Confirm the release is the problem.**

   ```bash
   kubectl -n orders rollout status deploy/orders-api --timeout=30s
   ```

2. **Roll back.**

   ```bash
   kubectl -n orders rollout undo deploy/orders-api
   ```

3. **Check health.**

   ```bash
   curl -s http://orders.localhost:8080/healthz
   ```

   You should see `ok`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `rollout undo` does nothing | Only one revision exists | Deploy the last good image tag by hand |
| Health check still fails | The database migration is not backward compatible | See the [service reference](/reference/service-reference/) for the schema version |

Never paste a secret value into a runbook. Name the secret and where it lives.
