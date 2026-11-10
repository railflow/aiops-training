-- The five most recent failed requests, each with the error log line that belongs to the same trace.
SELECT t.TraceId, t.ServiceName, t.SpanName, round(t.Duration / 1e6, 1) AS ms, l.Body AS log_line
FROM (
    SELECT TraceId, ServiceName, SpanName, Duration, Timestamp
    FROM otel.otel_traces
    WHERE Timestamp > now() - INTERVAL 15 MINUTE AND StatusCode IN ('Error', 'STATUS_CODE_ERROR')
      AND SpanKind IN ('Server', 'SPAN_KIND_SERVER')
    ORDER BY Timestamp DESC LIMIT 5
) AS t
LEFT JOIN otel.otel_logs AS l ON l.TraceId = t.TraceId AND l.SeverityText IN ('ERROR', 'Error', 'error')
ORDER BY t.Timestamp DESC;
