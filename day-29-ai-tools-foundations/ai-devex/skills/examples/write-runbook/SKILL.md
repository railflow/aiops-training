---
name: write-runbook
description: Draft an on-call runbook from an alert definition and recent incidents. Use when a new alert is added or an alert has no runbook link.
owner: platform-team
version: 1.2.0
---

# Write a runbook

1. Read the alert rule and the last three incidents that fired it.
2. Fill the template in `templates/runbook.md`: symptoms, first checks, safe fixes, escalation.
3. Link the runbook from the alert's annotations. Never paste credentials into it.
