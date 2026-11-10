-- What is failing, most often? Group error logs by message.
SELECT ServiceName, substring(Body, 1, 120) AS message, count() AS occurrences, max(Timestamp) AS last_seen
FROM otel.otel_logs
WHERE Timestamp > now() - INTERVAL 30 MINUTE AND SeverityText IN ('ERROR', 'Error', 'error')
GROUP BY ServiceName, message
ORDER BY occurrences DESC
LIMIT 15;
