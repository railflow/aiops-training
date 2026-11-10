-- LIST THE NAMES FIRST. Metric names and which table (gauge or sum) holds them depend on the
-- receiver versions you run. Every other query in this folder assumes names you have confirmed here.
SELECT 'gauge' AS tbl, MetricName, count() AS points
FROM otel.otel_metrics_gauge GROUP BY MetricName
UNION ALL
SELECT 'sum' AS tbl, MetricName, count() AS points
FROM otel.otel_metrics_sum GROUP BY MetricName
ORDER BY tbl, points DESC
LIMIT 60;
