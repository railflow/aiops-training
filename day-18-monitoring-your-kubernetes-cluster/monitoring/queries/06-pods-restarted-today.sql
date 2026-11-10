-- Containers whose restart counter increased today. The counter only goes up, so max - min is "restarts today".
-- (If query 01 shows k8s.container.restarts in otel_metrics_sum instead, change the table name.)
SELECT ResourceAttributes['k8s.namespace.name'] AS namespace,
       ResourceAttributes['k8s.pod.name'] AS pod,
       ResourceAttributes['k8s.container.name'] AS container,
       max(Value) - min(Value) AS restarts_today
FROM otel.otel_metrics_gauge
WHERE MetricName = 'k8s.container.restarts' AND TimeUnix >= toStartOfDay(now())
GROUP BY namespace, pod, container
HAVING restarts_today > 0
ORDER BY restarts_today DESC;
