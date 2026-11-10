-- RED in one query: requests, error percentage and latency percentiles per service per minute.
-- Verify first: SELECT DISTINCT SpanKind, StatusCode FROM otel.otel_traces  (spelling varies by exporter version)
SELECT toStartOfMinute(Timestamp) AS minute,
       ServiceName,
       count() AS requests,
       round(100 * countIf(StatusCode IN ('Error', 'STATUS_CODE_ERROR')) / count(), 2) AS error_pct,
       round(quantile(0.50)(Duration) / 1e6, 1) AS p50_ms,
       round(quantile(0.95)(Duration) / 1e6, 1) AS p95_ms,
       round(quantile(0.99)(Duration) / 1e6, 1) AS p99_ms
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 30 MINUTE AND SpanKind IN ('Server', 'SPAN_KIND_SERVER')
GROUP BY minute, ServiceName
ORDER BY minute, ServiceName;
