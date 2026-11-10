# Day 18: Monitoring your Kubernetes cluster: limits, layers and cluster metrics in ClickHouse: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

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
