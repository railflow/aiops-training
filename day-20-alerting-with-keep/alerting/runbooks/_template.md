# Runbook: <alert name>

**Owner:** <team>   **Severity:** <critical | high | warning | info>   **Last reviewed:** <date>

## What this alert means
One or two sentences in user terms. Which users, which feature, what they experience.

## Symptoms and first look (5 minutes)
- Dashboard: <link to the Grafana dashboard and panel>
- Query to run: <path to the SQL in day-20-alerting-with-keep/alerting/queries/ or the exact command>
- Is it getting worse? Is it one pod, one endpoint, or everything?

## Likely causes, most common first
1. A recent deploy or config change: `kubectl -n apps rollout history deploy/<name>`
2. A dependency failing: look at the slowest failed trace, which child span fails?
3. Resource limits: restarts, memory near limit, CPU at limit
4. The platform: node pressure, many services affected at once

## Mitigation (stop the bleeding)
- Roll back: `kubectl -n apps rollout undo deploy/<name>` (or `git revert` in the config repo if Flux manages it)
- Scale or raise a limit (temporary, then fix the manifest in git)
- Disable the feature flag or fault: <how>

## Verify recovery
- The alert resolves in Keep within <N> minutes
- Dashboard panel back to baseline

## Who to call
- Primary on-call: see `oncall/schedule.json`
- Escalation after 5 minutes without acknowledgement: secondary on-call
- Platform team (for node or cluster problems): <channel>

## After the incident
Write the blameless review (template in the Day 20 page). Update this runbook with what you learned.
