# Runbook: __APP__

**Owner:** replace me. **Last reviewed:** replace me.

## What it is

One paragraph. Who uses it, what breaks if it is down.

## How to tell it is healthy

- `curl http://__APP__.localhost:8080/readyz` returns 200.
- Dashboard: replace me. Alerts: replace me.

## Common problems

| Symptom | Likely cause | What to do |
|---|---|---|
| `/readyz` returns 503 | Database unreachable | `kubectl -n __APP__ logs deploy/__APP__`; check the database and the Secret |
| Pods `CrashLoopBackOff` | Bad config or image | `kubectl -n __APP__ describe pod`; roll back the tag in the config repo |

## Roll back

Revert the commit in the config repo that changed the image tag. Flux applies it. Do not `kubectl edit` in production.

> Never put passwords, tokens or keys in this file.
