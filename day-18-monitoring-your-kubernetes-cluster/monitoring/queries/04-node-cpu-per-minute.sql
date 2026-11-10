-- Node CPU usage in cores, per minute. (k8s.node.cpu.usage is a gauge in cores in current versions;
-- older versions emit k8s.node.cpu.utilization instead: check query 01.)
SELECT toStartOfMinute(TimeUnix) AS minute,
       ResourceAttributes['k8s.node.name'] AS node,
       round(avg(Value), 3) AS cpu_cores
FROM otel.otel_metrics_gauge
WHERE MetricName = 'k8s.node.cpu.usage' AND TimeUnix > now() - INTERVAL 30 MINUTE
GROUP BY minute, node
ORDER BY minute, node;
