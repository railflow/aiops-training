---
title: "Day 18: Monitoring your Kubernetes cluster: limits, layers and cluster metrics in ClickHouse"
description: "Files in day-18-monitoring-your-kubernetes-cluster/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 18: Monitoring your Kubernetes cluster: limits, layers and cluster metrics in ClickHouse"
  order: 18
---

This page is the file-by-file guide to [`day-18-monitoring-your-kubernetes-cluster/`](https://github.com/railflow/aiops-training/tree/main/day-18-monitoring-your-kubernetes-cluster) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Look at every layer from your laptop to your process by hand, load it with k6, see why that does not scale, then ship node, pod and cluster metrics to ClickHouse automatically.

Homework for this day is in [`day-18-monitoring-your-kubernetes-cluster/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-18-monitoring-your-kubernetes-cluster/homework.md) and is repeated at the bottom of this page.

## What is in the folder

24 files. Paths below are relative to the repo root unless noted.

### day-18-monitoring-your-kubernetes-cluster/monitoring/

| File | What it is | How the lesson uses it |
|---|---|---|
| `monitoring/hpa-demo.yaml` | Autoscaling demo: HorizontalPodAutoscaler needs metrics-server and a CPU REQUEST on the pods (utilisation is measured against the request). | `kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/hpa-demo.yaml` |
| `monitoring/kind-config-multinode.yaml` | OPTIONAL: a 3-node kind cluster (1 control plane + 2 workers). Every node is a Docker container with its own kubelet and containerd, so this MULTIPLIES memory use (roughly 3x the idle footprint of one node). Use a different cluster name so it does not touch ai-ops-training: Defines: Cluster. | `kind create cluster --config day-18-monitoring-your-kubernetes-cluster/monitoring/kind-config-multinode.yaml` |
| `monitoring/metrics-server-values.yaml` | metrics-server on kind. Chart: metrics-server/metrics-server (helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/). | `helm upgrade --install metrics-server metrics-server/metrics-server --version 3.14.0 -n kube-system -f day-18-monitoring-your-kubernetes-cluster/mo...` |
| `monitoring/oom-demo.yaml` | OOMKill demo: a 64Mi memory LIMIT. /alloc?mb=100 keeps 100 MB, so the kernel kills the container, the kubelet restarts it, and `kubectl describe pod` shows "Last State: Terminated, Reason: OOMKilled". Defines: Deployment, Service. | `kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/oom-demo.yaml` |
| `monitoring/quota-demo.yaml` | Namespace-level limits: a ResourceQuota caps the TOTAL a namespace may request; a LimitRange gives containers defaults and per-container bounds. Optional exercise. Defines: Namespace, ResourceQuota, LimitRange. | `kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/quota-demo.yaml` |
| `monitoring/throttle-demo.yaml` | CPU throttling demo: a deliberately small CPU LIMIT. /burn?ms=200 needs far more CPU than 100m allows, so the kernel pauses the container (CFS throttling) and latency rises while CPU use looks "capped". Defines: Deployment, Service, Ingress. | `kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/throttle-demo.yaml` |

### day-18-monitoring-your-kubernetes-cluster/monitoring/k6/

| File | What it is | How the lesson uses it |
|---|---|---|
| `monitoring/k6/load.js` | LOAD: ramp up to a normal-busy level, hold, ramp down. "Does it hold up at the traffic we expect?" Laptop-safe default is 20 virtual users; raise it deliberately: k6 run -e MAX_VUS=50 load.js |  |
| `monitoring/k6/loop.js` | LOOP: a steady, low request RATE that runs for a long time, so dashboards always have live data. |  |
| `monitoring/k6/smoke.js` | SMOKE: one virtual user for 30 seconds. "Does it work at all?" Run this before anything bigger. | `docker run --rm -i grafana/k6 run - < day-18-monitoring-your-kubernetes-cluster/monitoring/k6/smoke.js` |
| `monitoring/k6/spike.js` | SPIKE: a sudden jump in traffic, then back to normal. "Do we survive a burst, and how fast do we recover?" |  |
| `monitoring/k6/stress.js` | STRESS: keep increasing the load until something hurts. "Where is the limit, and what breaks first?" WARNING: |  |

### day-18-monitoring-your-kubernetes-cluster/monitoring/otel/

| File | What it is | How the lesson uses it |
|---|---|---|
| `monitoring/otel/agent-explicit-values.yaml` | The SAME agent as agent-values.yaml, with the presets replaced by what they generate, so you can see every moving part. Use ONE of the two files, not both (they create the same release name). |  |
| `monitoring/otel/agent-values.yaml` | AGENT collector: one pod per node (DaemonSet). Collects node, pod and container metrics from the local kubelet and forwards them to the gateway from Day 17. | `helm template agent open-telemetry/opentelemetry-collector --version 0.178.2 -n observability -f day-18-monitoring-your-kubernetes-cluster/monitori...` |
| `monitoring/otel/cluster-values.yaml` | CLUSTER collector: exactly ONE replica (Deployment). The k8s_cluster receiver asks the API server for cluster-wide state (pod phase, deployment desired/available, node conditions, restarts). | `-f day-18-monitoring-your-kubernetes-cluster/monitoring/otel/cluster-values.yaml` |

### day-18-monitoring-your-kubernetes-cluster/monitoring/queries/

| File | What it is | How the lesson uses it |
|---|---|---|
| `monitoring/queries/01-metric-names.sql` | LIST THE NAMES FIRST. Metric names and which table (gauge or sum) holds them depend on the receiver versions you run. Every other query in this folder assumes names you have confirmed here. |  |
| `monitoring/queries/02-pod-memory-over-time.sql` | Memory (working set, MiB) of one pod, per minute, last 30 minutes. Edit the pod name prefix. | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/02-pod-memory-over-time.sql \| ch` |
| `monitoring/queries/03-top-memory-pods.sql` | Top 10 pods by working-set memory right now (latest value per pod in the last 5 minutes). | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/03-top-memory-pods.sql \| ch` |
| `monitoring/queries/04-node-cpu-per-minute.sql` | Node CPU usage in cores, per minute. (k8s.node.cpu.usage is a gauge in cores in current versions; older versions emit k8s.node.cpu.utilization instead: check query 01.) | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/04-node-cpu-per-minute.sql \| ch` |
| `monitoring/queries/05-top5-pods-cpu-15m.sql` | Top 5 pods by CPU over the last 15 minutes: average and p95-ish (95th percentile of the samples). | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/05-top5-pods-cpu-15m.sql \| ch` |
| `monitoring/queries/06-pods-restarted-today.sql` | Containers whose restart counter increased today. The counter only goes up, so max - min is "restarts today". (If query 01 shows k8s.container.restarts in otel_metrics_sum instead, change the table name.) | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/06-pods-restarted-today.sql \| ch` |
| `monitoring/queries/07-replicas-desired-vs-available.sql` | Deployment replicas, desired versus available, per minute (from the k8s_cluster receiver). | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/07-replicas-desired-vs-available.sql \| ch` |
| `monitoring/queries/08-filter-by-cluster.sql` | Every cluster that is sending data, and how fresh it is. With one cluster you see one row; with hundreds, this is how you notice one went quiet. | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/08-filter-by-cluster.sql \| ch` |
| `monitoring/queries/09-storage-and-ttl.sql` | How much disk each telemetry table uses, and its retention rule. | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/09-storage-and-ttl.sql \| ch` |
| `monitoring/queries/10-simulated-second-cluster.sql` | SIMULATION ONLY: copies the last 10 minutes of ai-ops-training metrics and labels the copy "heyjob-simulated-b", to show what a second cluster looks like in the same table. | `cat day-18-monitoring-your-kubernetes-cluster/monitoring/queries/10-simulated-second-cluster.sql \| ch` |

## Files this day uses from other folders

From [Day 17](/days/day-17-observability/): `day-17-observability/` (`observability/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo update
helm show values metrics-server/metrics-server | grep -n -A5 "^defaultArgs\|^args"
helm upgrade --install metrics-server metrics-server/metrics-server --version 3.14.0 -n kube-system -f day-18-monitoring-your-kubernetes-cluster/monitoring/metrics-server-values.yaml
kubectl -n kube-system rollout status deploy/metrics-server --timeout=180s
```

```bash
kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/quota-demo.yaml
kubectl -n quota-demo describe resourcequota compute
kubectl -n quota-demo run big --image=busybox:1.36 --restart=Never --overrides='{"spec":{"containers":[{"name":"big","image":"busybox:1.36","command":["sleep","3600"],"resources":{"requests":{"memory":"2Gi"}}}]}}'
```

```bash
brew install k6
k6 version
# No install? Run it in Docker:
docker run --rm -i grafana/k6 run - < day-18-monitoring-your-kubernetes-cluster/monitoring/k6/smoke.js
```

```bash
cd day-18-monitoring-your-kubernetes-cluster/monitoring/k6
k6 run smoke.js
```

```bash
kubectl apply -f day-18-monitoring-your-kubernetes-cluster/monitoring/throttle-demo.yaml
kubectl -n apps rollout status deploy/shop-throttle
cd day-18-monitoring-your-kubernetes-cluster/monitoring/k6
k6 run -e BASE_URL=http://throttle.localhost:8080 -e TARGET_PATH='/burn?ms=100' -e MAX_VUS=5 load.js
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
defaultArgs:
  - --cert-dir=/tmp
  - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
  - --kubelet-use-node-status-port
  - --metric-resolution=15s
args: []
deployment "metrics-server" successfully rolled out
```

```text
Name:            compute
Resource         Used  Hard
limits.memory    0     1Gi
pods             0     5
Error from server (Forbidden): pods "big" is forbidden: exceeded quota: compute, requested: requests.memory=2Gi, used: requests.memory=0, limited: requests.memory=512Mi
```

## How these files relate to other days and shared tools

- Builds on [Day 7](/days/day-07-traefik-ingress/), [Day 17](/days/day-17-observability/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 17](/days/day-17-observability/).
- Files from this folder are used by [Day 19](/days/day-19-observability-dashboards/).

## Homework

Work in `~/heyjob-labs/day18/`.

### Exercise 1: Limits table for your machine

**Do:** fill in this table with your own numbers and the command that produced each:

| Layer | CPUs | Memory | Limit set by | Command |
|---|---|---|---|---|
| Host | | | | |
| Docker VM (or WSL2) | | | | |
| kind node | | | | |
| One pod (request / limit) | | | | |

### Exercise 2: Before, during, after

**Do:** capture `kubectl top pods -A --sort-by=cpu` before, during, and after a k6 `load.js` run (at least 20 VUs against `hpa.localhost`), and the k6 summary.

### Exercise 3: Break it two ways

**Do:** trigger an OOMKill and CPU throttling, and write a short diagnosis for each: the symptom, the **evidence** (command and the output lines that prove it), and the fix.

### Exercise 4: Watch the autoscaler

**Do:** change the HPA `averageUtilization` to 30 and `maxReplicas` to 3, re-run the load, and record when replicas change.

### Exercise 5: Find the same pod in ClickHouse

**Do:** find one pod's working-set memory in `kubectl top` and in ClickHouse (`02-pod-memory-over-time.sql`).

### Exercise 6: Two queries

**Do:** write queries for "top 5 pods by CPU in the last 15 minutes" (p95-ish) and "pods that restarted today". Trigger a restart first (`kubectl -n apps delete pod ...` does not increase the restart counter; an OOMKill does).

### Exercise 7: Why the cluster label matters

**Do:** add a second `resource` attribute to both collectors, `environment=local`, and explain in five sentences why `k8s.cluster.name` matters at 100 clusters (think: duplicate pod names, comparing environments, finding a silent cluster).

### Exercise 8 (optional): Multi-node

**Do:** create the multi-node kind cluster, deploy 6 replicas, show the spread, and compare `docker stats` before and after creating it.

### Exercise 9: Break the pipeline

**Do:** do step 27 and one more break of your choice (delete the `otel-agent` ClusterRoleBinding, for example). Write the symptom, the log line, and the fix for each.
