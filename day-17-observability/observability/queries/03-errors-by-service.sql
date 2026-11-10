-- Error-level logs in the last 15 minutes, per service.
SELECT ServiceName, count() AS errors
FROM otel.otel_logs
WHERE Timestamp > now() - INTERVAL 15 MINUTE
  AND SeverityText IN ('ERROR', 'Error', 'error')
GROUP BY ServiceName
ORDER BY errors DESC;
