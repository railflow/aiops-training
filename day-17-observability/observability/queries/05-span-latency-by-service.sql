-- Request count and latency percentiles per service and span name (Duration is nanoseconds).
SELECT ServiceName, SpanName,
       count() AS spans,
       round(quantile(0.50)(Duration) / 1e6, 1) AS p50_ms,
       round(quantile(0.95)(Duration) / 1e6, 1) AS p95_ms,
       round(quantile(0.99)(Duration) / 1e6, 1) AS p99_ms
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 15 MINUTE
GROUP BY ServiceName, SpanName
ORDER BY p95_ms DESC
LIMIT 20;
