---
title: "Day 20: Alerting and incident management with Keep"
description: "Files in day-20-alerting-with-keep/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 20: Alerting and incident management with Keep"
  order: 20
---

This page is the file-by-file guide to [`day-20-alerting-with-keep/`](https://github.com/railflow/aiops-training/tree/main/day-20-alerting-with-keep) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Decide what deserves a page, send every signal through one open-source alert hub (Keep), route notifications, and run the incident that follows, including on-call, escalation, runbooks and a blameless review.

Homework for this day is in [`day-20-alerting-with-keep/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-20-alerting-with-keep/homework.md) and is repeated at the bottom of this page.

## What is in the folder

35 files. Paths below are relative to the repo root unless noted.

### day-20-alerting-with-keep/alerting/

| File | What it is | How the lesson uses it |
|---|---|---|
| `alerting/sinks.yaml` | Local notification sinks so you can see exactly what Keep would send, with no external accounts. | `kubectl apply -f day-20-alerting-with-keep/alerting/sinks.yaml` |

### day-20-alerting-with-keep/alerting/keep/

| File | What it is | How the lesson uses it |
|---|---|---|
| `alerting/keep/create-secrets.ps1` | Creates the Kubernetes Secrets Keep needs, with generated values. | `Get-Content "$HOME\aiops-training\day-20-alerting-with-keep\alerting\keep\create-secrets.ps1"` |
| `alerting/keep/create-secrets.sh` | Creates the Kubernetes Secrets Keep needs, with generated values. | `cat day-20-alerting-with-keep/alerting/keep/create-secrets.sh` |
| `alerting/keep/kustomization.yaml` | Alerts as code: every file in workflows/ becomes a key in the ConfigMap keep-workflow-files, which values-keep.yaml mounts at /workflows. Keep reads that directory at start-up (KEEP_WORKFLOWS_DIRECTORY) and adds, updates or removes workflows to match the files. Defines: Kustomization. |  |
| `alerting/keep/optional-notify-slack.yaml` | NOT included in kustomization.yaml: it needs a real Slack account. |  |
| `alerting/keep/values-keep.yaml` | Keep (open-source alert management) on kind, behind Traefik at http://keep.localhost:8080. Chart: keephq/keep (helm repo add keephq https://keephq.github.io/helm-charts). Compare with: helm show values keephq/keep --version 0.1.97 \| less | `-f day-20-alerting-with-keep/alerting/keep/values-keep.yaml` |
| `alerting/keep/workflows/10-error-rate.yaml` | Generated from queries/01-error-rate-5m.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/11-p95-latency.yaml` | Generated from queries/02-p95-latency-5m.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/12-no-traffic.yaml` | Generated from queries/03-no-traffic-dead-mans-switch.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/13-pod-restarts.yaml` | Generated from queries/04-pod-restarts-15m.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/14-oom-suspects.yaml` | Generated from queries/05-oom-suspects-10m.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/15-replicas-unavailable.yaml` | Generated from queries/06-replicas-unavailable.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/16-memory-near-limit.yaml` | Generated from queries/07-memory-over-90-percent-of-limit.sql. |  |
| `alerting/keep/workflows/17-synthetic-traffic.yaml` | Generated from queries/08-synthetic-traffic-flowing.sql. Compare the SQL to keep the two in sync. |  |
| `alerting/keep/workflows/20-notify-critical.yaml` | The ONE place that decides who hears about an alert. Everything (ClickHouse workflows, Gatus, Grafana) sends alerts INTO Keep; only this workflow (and 30-/40-) sends messages OUT. |  |
| `alerting/keep/workflows/30-escalate-unacknowledged.yaml` | Escalation SKETCH: if a critical alert has been firing for more than 5 minutes and nobody acknowledged it, email the secondary on-call. |  |
| `alerting/keep/workflows/40-incident-opened.yaml` | When Keep opens an incident (from a correlation rule, see the lesson), post one message per incident to the webhook sink. The trigger field is "events" (the Keep code reads "events"; one doc page says "on": check the docs). |  |

### day-20-alerting-with-keep/alerting/oncall/

| File | What it is | How the lesson uses it |
|---|---|---|
| `alerting/oncall/rotate.py` | Work out who is on call this week from schedule.json and (optionally) write it into the Keep workflows. | `python3 day-20-alerting-with-keep/alerting/oncall/rotate.py` |
| `alerting/oncall/schedule.json` | JSON data or configuration file. |  |

### day-20-alerting-with-keep/alerting/queries/

| File | What it is | How the lesson uses it |
|---|---|---|
| `alerting/queries/01-error-rate-5m.sql` | Alert: high error rate. Percentage of failed server spans in the last 5 minutes for the user-facing service (symptom-based: |  |
| `alerting/queries/02-p95-latency-5m.sql` | Alert: slow checkout. p95 duration (milliseconds) of the user-facing /checkout server span over the last 5 minutes. |  |
| `alerting/queries/03-no-traffic-dead-mans-switch.sql` | Alert: "dead man's switch". Silence is also a failure: if no spans AND no logs arrive, either the service is down or the telemetry pipeline is broken. Always returns one row. |  |
| `alerting/queries/04-pod-restarts-15m.sql` | Alert: containers restarting. The restart counter only goes up, so max - min inside the window is "restarts in the window". If query 01 of Day 18 shows the metric in otel_metrics_sum, change the table. |  |
| `alerting/queries/05-oom-suspects-10m.sql` | Alert: probable OOMKill. The metrics here do not carry the termination reason, so this is a PROXY: |  |
| `alerting/queries/06-replicas-unavailable.sql` | Alert: fewer replicas available than desired for a Deployment, using the latest value in the last 3 minutes. |  |
| `alerting/queries/07-memory-over-90-percent-of-limit.sql` | Alert: a pod is using more than 90% of its memory limit (an OOMKill is likely soon). |  |
| `alerting/queries/08-synthetic-traffic-flowing.sql` | Alert: the synthetic load (k6) is not arriving. Requests whose user agent starts with "k6" in the last 5 minutes. |  |

### day-20-alerting-with-keep/alerting/runbooks/

| File | What it is | How the lesson uses it |
|---|---|---|
| `alerting/runbooks/_template.md` | Document: Runbook: &lt;alert name&gt; |  |
| `alerting/runbooks/high-error-rate.md` | Document: Runbook: High error rate on shop-frontend |  |
| `alerting/runbooks/no-traffic.md` | Document: Runbook: No telemetry from shop-frontend (dead man's switch) |  |
| `alerting/runbooks/oomkilled.md` | Document: Runbook: Probable OOMKill / memory near limit |  |
| `alerting/runbooks/pod-restarts.md` | Document: Runbook: Containers restarting |  |
| `alerting/runbooks/replicas-unavailable.md` | Document: Runbook: Fewer replicas available than desired |  |
| `alerting/runbooks/slow-requests.md` | Document: Runbook: Slow checkout |  |
| `alerting/runbooks/synthetic-traffic.md` | Document: Runbook: Synthetic traffic (k6) is not arriving |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cat day-20-alerting-with-keep/alerting/keep/create-secrets.sh
day-20-alerting-with-keep/alerting/keep/create-secrets.sh
```

```bash
kubectl apply -f day-20-alerting-with-keep/alerting/sinks.yaml
kubectl apply -k day-20-alerting-with-keep/alerting/keep
```

```bash
helm upgrade --install keep keephq/keep --version 0.1.97 -n keep \
-f day-20-alerting-with-keep/alerting/keep/values-keep.yaml
kubectl -n keep rollout status deploy/keep-backend --timeout=300s
```

```bash
cd day-20-alerting-with-keep/alerting/queries
for f in 01 02 03 04 07; do echo "== $f"; ch < $f-*.sql; done
```

```bash
python3 day-20-alerting-with-keep/alerting/oncall/rotate.py
python3 day-20-alerting-with-keep/alerting/oncall/rotate.py --date 2026-11-17
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
namespace/keep configured
secret/keep-auth created
secret/keep-ui created
secret/keep-providers created
Secrets created in namespace keep: keep-auth, keep-ui, keep-providers.
```

```text
deployment.apps/mailpit created
service/mailpit created
ingress.networking.k8s.io/mailpit created
deployment.apps/echo-sink created
service/echo-sink created
configmap/keep-workflow-files created
```

## How these files relate to other days and shared tools

- Builds on [Day 16](/days/day-16-secrets-management-openbao/), [Day 17](/days/day-17-observability/), [Day 19](/days/day-19-observability-dashboards/) (cluster, images or secrets created there).
- Refers to files in [Day 17](/days/day-17-observability/) (for example from `day-20-alerting-with-keep/alerting/runbooks/high-error-rate.md`).
- Files from this folder are used by [Day 32](/days/day-32-incident-to-reviewed-pr/).

## Homework

Work in `~/heyjob-labs/day20/`.

### Exercise 1: Interview, then catalog

**Do:** write the interview questions for a **developer** and an **infrastructure engineer** (at least five each), "interview" two classmates or colleagues (or role-play both with an AI and then challenge its answers), and produce an alert catalog table with at least ten rows using the template above. Include two security alerts and one platform alert (node not ready) you will implement.

### Exercise 2: Two new alerts that fire and resolve

**Do:** implement two new alerts as ClickHouse queries and Keep workflows (for example error logs for a service in 5 minutes, and a node-condition alert), following the `fire` / `resolve` pattern. Trigger both with k6 or fault injection and capture the firing and resolved states.

### Exercise 3: Runbook and severity

**Do:** write a runbook for each new alert from `_template.md` and link it from the alert's `labels.runbook`. Assign severities and justify each in one sentence.

### Exercise 4: A notification sink and a captured payload

**Do:** point one alert at the echo sink and save the exact JSON it received. Then explain, in five lines, how you would map that payload to PagerDuty or Slack.

### Exercise 5: Escalation policy and rotation file

**Do:** write your own `schedule.json` for three people with one holiday override, run `rotate.py` for four different dates, and write the escalation policy in plain words (who, after how many minutes, and what "acknowledged" means).

### Exercise 6: Game day and blameless review

**Do:** run the game day from step 27 with a partner and write the review.

### Exercise 7: Break it

**Do:** recreate the `keep-providers` Secret with a **wrong ClickHouse password**, restart `keep-backend`, and diagnose from Keep's logs and ClickHouse's logs why the workflows fail. Then restore it.
