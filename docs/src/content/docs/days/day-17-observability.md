---
title: "Day 17: Observability: logs, metrics and traces with OpenTelemetry and ClickHouse"
description: "Files in day-17-observability/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 17: Observability: logs, metrics and traces with OpenTelemetry and ClickHouse"
  order: 17
---

This page is the file-by-file guide to [`day-17-observability/`](https://github.com/railflow/aiops-training/tree/main/day-17-observability) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Emit structured logs and traces from an app, collect them with an OpenTelemetry Collector, store them in ClickHouse on kind, and answer questions with SQL.

Homework for this day is in [`day-17-observability/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-17-observability/homework.md) and is repeated at the bottom of this page.

## What is in the folder

17 files. Paths below are relative to the repo root unless noted.

### day-17-observability/observability/

| File | What it is | How the lesson uses it |
|---|---|---|
| `observability/clickhouse.yaml` | ClickHouse for the observability labs (single node, learning only). Create the password Secret FIRST, on the command line (never commit it): kubectl -n observability create secret generic clickhouse-credentials --from-literal=password="&lt;generated&gt;" Defines: Namespace, Service, StatefulSet. | `kubectl apply -f day-17-observability/observability/clickhouse.yaml` |
| `observability/otel-gateway-values.yaml` | Gateway collector: the single front door for all telemetry, writing to ClickHouse. | `helm upgrade --install otel-gateway open-telemetry/opentelemetry-collector --version 0.178.2 -n observability -f day-17-observability/observability...` |
| `observability/shop.yaml` | Two deployments of the SAME image (shop-observability:1.0): a frontend that calls a backend. Telemetry goes to the gateway collector; faults are OFF unless you set INJECT_* (see app.py). Defines: Namespace, Deployment, Service, Deployment and 2 more. |  |
| `observability/telemetrygen-job.yaml` | Sends synthetic traces, then logs, to the gateway so you can prove the pipeline before real apps exist. Image and flags: check https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/cmd/telemetrygen Defines: Job. | `kubectl apply -f day-17-observability/observability/telemetrygen-job.yaml` |

### day-17-observability/observability/queries/

| File | What it is | How the lesson uses it |
|---|---|---|
| `observability/queries/01-tables-and-schema.sql` | Run these first. Column names come from the exporter version you installed; trust DESCRIBE over this course. |  |
| `observability/queries/02-recent-logs.sql` | Newest 20 log lines from any service. |  |
| `observability/queries/03-errors-by-service.sql` | Error-level logs in the last 15 minutes, per service. | `cat day-17-observability/observability/queries/03-errors-by-service.sql \| ch` |
| `observability/queries/04-logs-for-one-trace.sql` | Every log line of one request. Run with a real id, for example: clickhouse-client --param_trace_id=&lt;32 hex chars&gt; --queries-file 04-logs-for-one-trace.sql |  |
| `observability/queries/05-span-latency-by-service.sql` | Request count and latency percentiles per service and span name (Duration is nanoseconds). | `cat day-17-observability/observability/queries/05-span-latency-by-service.sql \| ch` |
| `observability/queries/06-slowest-traces.sql` | The 10 slowest root spans (no parent) in the last hour: pick a TraceId and look at it. |  |
| `observability/queries/07-one-trace-tree.sql` | All spans of one trace, in time order. Use --param_trace_id as in 04. |  |
| `observability/queries/08-failed-spans.sql` | Which StatusCode strings exist in YOUR data? (Spelling differs between exporter versions.) |  |

### day-17-observability/observability/shop/

| File | What it is | How the lesson uses it |
|---|---|---|
| `observability/shop/Dockerfile` | Container image recipe (base `python:3.12-slim`). |  |
| `observability/shop/app.py` | A tiny two-tier "shop" used for observability, monitoring and dashboard labs. |  |
| `observability/shop/gunicorn.conf.py` | Gunicorn settings. OpenTelemetry must be started AFTER the worker forks, because exporter threads do not survive a fork; post_fork is the documented place for that. |  |
| `observability/shop/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `observability/shop/telemetry.py` | OpenTelemetry setup: traces and logs go to the collector over OTLP/HTTP. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
kubectl -n observability create secret generic clickhouse-credentials \
--from-literal=password="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)"
kubectl apply -f day-17-observability/observability/clickhouse.yaml
kubectl -n observability rollout status statefulset/clickhouse --timeout=300s
```

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update
helm show values open-telemetry/opentelemetry-collector | grep -n -E "^(mode|image|fullnameOverride|extraEnvs|config):"
helm upgrade --install otel-gateway open-telemetry/opentelemetry-collector --version 0.178.2 -n observability -f day-17-observability/observability/otel-gateway-values.yaml
kubectl -n observability rollout status deploy/otel-gateway --timeout=180s
```

```bash
kubectl apply -f day-17-observability/observability/telemetrygen-job.yaml
kubectl -n observability wait --for=condition=complete job/telemetrygen --timeout=120s
kubectl -n observability logs deploy/otel-gateway | grep -E "Traces|Logs" | tail -n 4
```

```bash
cd day-17-observability/observability
docker build -t shop-observability:1.0 shop
kind load docker-image shop-observability:1.0 --name ai-ops-training
kubectl apply -f shop.yaml
kubectl -n apps rollout status deploy/shop-backend deploy/shop-frontend --timeout=180s
```

```bash
cat day-17-observability/observability/queries/03-errors-by-service.sql | ch
cat day-17-observability/observability/queries/05-span-latency-by-service.sql | ch
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
namespace/observability created
secret/clickhouse-credentials created
statefulset.apps/clickhouse created
partitioned roll out complete: 1 new pods have been updated...
```

```text
Release "otel-gateway" does not exist. Installing it now.
NAME: otel-gateway
STATUS: deployed
deployment "otel-gateway" successfully rolled out
```

## How these files relate to other days and shared tools

- Builds on [Day 3](/days/day-03-kind-kubernetes/), [Day 7](/days/day-07-traefik-ingress/), [Day 16](/days/day-16-secrets-management-openbao/) (cluster, images or secrets created there).
- Files from this folder are used by [Day 18](/days/day-18-monitoring-your-kubernetes-cluster/), [Day 19](/days/day-19-observability-dashboards/), [Day 20](/days/day-20-alerting-with-keep/).

## Homework

Work in `~/heyjob-labs/day17/`.

### Exercise 1: Signals table

**Do:** write three questions about the shop app, one best answered by logs, one by metrics, one by traces, and justify each.

### Exercise 2: Percentiles

**Do:** write a ClickHouse query for p50, p95, and p99 latency of `shop-backend` over the last 30 minutes, split by minute (`toStartOfMinute(Timestamp)`).

### Exercise 3: Find the failing request

**Do:** generate failures with `/flaky?rate=0.5`. From the **logs** alone, find a `TraceId` of a failed request, then fetch its span tree.

### Exercise 4: Add a field

**Do:** add a `customer` field to the JSON log of `/checkout` (read it from a query parameter). Rebuild as `shop-observability:1.1`, redeploy, and query for it. (Hint: it ends up in `LogAttributes` or in the `Body`, depending on the SDK; `DESCRIBE` and a `SELECT *` show which.)

### Exercise 5: Retention

**Do:** run `SHOW CREATE TABLE otel.otel_logs` and find the TTL. Explain what it deletes and when, and what happens to disk if you set it to 365 days.

### Exercise 6: Break it differently

**Do:** break the pipeline another way (wrong password in the Secret, or delete the Service). Record the exact collector log line that identified the cause.
