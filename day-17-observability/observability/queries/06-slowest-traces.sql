-- The 10 slowest root spans (no parent) in the last hour: pick a TraceId and look at it.
SELECT TraceId, ServiceName, SpanName, round(Duration / 1e6, 1) AS ms, StatusCode
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 1 HOUR AND ParentSpanId = ''
ORDER BY Duration DESC
LIMIT 10;
