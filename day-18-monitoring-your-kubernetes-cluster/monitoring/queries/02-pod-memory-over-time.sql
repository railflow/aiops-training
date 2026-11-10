-- Memory (working set, MiB) of one pod, per minute, last 30 minutes. Edit the pod name prefix.
SELECT toStartOfMinute(TimeUnix) AS minute,
       round(max(Value) / 1048576, 1) AS memory_mib
FROM otel.otel_metrics_gauge
WHERE MetricName = 'k8s.pod.memory.working_set'
  AND ResourceAttributes['k8s.pod.name'] LIKE 'shop-frontend%'
  AND TimeUnix > now() - INTERVAL 30 MINUTE
GROUP BY minute
ORDER BY minute;
