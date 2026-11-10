# Day 17: Observability: logs, metrics and traces with OpenTelemetry and ClickHouse: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

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
