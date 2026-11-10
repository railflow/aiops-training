-- How much disk each telemetry table uses, and its retention rule.
SELECT table, formatReadableSize(sum(bytes_on_disk)) AS on_disk, sum(rows) AS rows
FROM system.parts
WHERE database = 'otel' AND active
GROUP BY table
ORDER BY sum(bytes_on_disk) DESC;

SHOW CREATE TABLE otel.otel_metrics_gauge;
