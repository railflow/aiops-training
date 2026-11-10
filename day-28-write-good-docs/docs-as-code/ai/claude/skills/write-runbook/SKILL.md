---
name: write-runbook
description: Write or update an operational runbook for a service. Use when asked for a runbook, on-call guide, or incident procedure.
---

# Write a runbook

1. Read the service's manifests, health endpoints, alerts and dependency list from the repository.
2. Start from `day-28-write-good-docs/docs-as-code/app-docs-template/docs/runbook.md`.
3. For every symptom: likely cause, the exact command to confirm it, the exact fix, who to escalate to.
4. Every command must be copy-pasteable. Mark any you could not run as "not run".
5. Never write a secret value. Write the path or name of the secret and how a person with access fetches it.
6. End with how to tell it is fixed.
