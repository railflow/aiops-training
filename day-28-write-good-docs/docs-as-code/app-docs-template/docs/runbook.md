# __APP__ runbook

> Written for the person paged at 03:00 who has never seen this service. Keep it short, exact and tested.
> **Never put secrets, tokens, passwords or internal-only URLs with credentials in this file.** Say where the secret lives
> (for example "OpenBao path `secret/__APP__/db`") and how to fetch it with your own access.

## Is it up?

- Dashboard: <link>   Alert: <name>   Health check: `GET /healthz` and `GET /readyz`
- `kubectl -n __APP__ get pods,deploy`

## Symptoms and first actions

| Symptom | Likely cause | What to do | Escalate to |
|---|---|---|---|
| 5xx rate rising | bad deploy | roll back: `flux suspend ...` then revert the commit | owner team |
| `/readyz` failing | database unreachable | check the database Secret and NetworkPolicy | platform team |

## Routine tasks

- Roll back: <exact steps>
- Rotate the database password: <exact steps, and who can do it>
- Scale: <exact steps>

## Dependencies

| Dependency | What breaks without it | Contact |
|---|---|---|
| Postgres (shared) | everything | platform team |

## After an incident

Write what happened in `docs/incidents/YYYY-MM-DD-title.md`: timeline, impact, cause, fix, follow-ups. No blame.
