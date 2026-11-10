# Day 19: Observability: dashboards as code with Grafana and ClickHouse: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day19/`.

### Exercise 1: Fifteen minutes of data

**Do:** run a k6 loop for 15 minutes. Take screenshots of all four dashboards, and export one panel's JSON (panel menu, Inspect, Panel JSON).

### Exercise 2: Three manual queries, three panels

**Do:** write three new ClickHouse queries of your own (for example "requests by HTTP route", "error log volume by pod", "memory growth per pod"). Run each by hand, then turn each into a dashboard panel.

### Exercise 3: A dashboard with a variable

**Do:** build a new dashboard with a `service` template variable (copy the pattern from the generator) and at least two panels that use it. Add it to `build_dashboards.py` and to `kustomization.yaml`, regenerate, and apply.

### Exercise 4: App next to infra

**Do:** add a panel for **error rate by endpoint** and a panel for **pod CPU** of the same service next to each other, and write one paragraph on what each of these mismatches would tell you: (a) errors up, CPU flat; (b) latency up, CPU at its limit; (c) errors up, restarts up.

### Exercise 5: The incident drill

**Do:** run both drill variants and fill in the post-incident note for each.

### Exercise 6: Prove it is code

**Do:** delete the Grafana pod and show the dashboards return; then change a panel title in the generator, apply, and show the change appear without any click in the UI.

### Exercise 7: Break it

**Do:** recreate the `grafana-clickhouse` Secret with a **wrong** password and restart Grafana. Diagnose from Grafana's logs and the ClickHouse logs.

### Exercise 8 (optional): Compare with another UI

**Do:** view the same traces and logs in HyperDX/ClickStack, SigNoz, or Metabase/Superset against the same ClickHouse (check each project's documentation; they may expect a different table layout).
