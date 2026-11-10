-- Any node condition that reported "under pressure" in the last hour (value 1 = true).
SELECT ResourceAttributes['k8s.node.name'] AS node, MetricName, max(Value) AS under_pressure, max(TimeUnix) AS last_seen
FROM otel.otel_metrics_gauge
WHERE MetricName IN ('k8s.node.condition_memory_pressure', 'k8s.node.condition_disk_pressure', 'k8s.node.condition_pid_pressure')
  AND TimeUnix > now() - INTERVAL 1 HOUR
GROUP BY node, MetricName
ORDER BY under_pressure DESC;
