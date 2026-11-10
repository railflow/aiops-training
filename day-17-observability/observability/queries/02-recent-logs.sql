-- Newest 20 log lines from any service.
SELECT Timestamp, ServiceName, SeverityText, TraceId, substring(Body, 1, 100) AS body
FROM otel.otel_logs
ORDER BY Timestamp DESC
LIMIT 20;
