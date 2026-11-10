-- Top 10 pods by working-set memory right now (latest value per pod in the last 5 minutes).
SELECT ResourceAttributes['k8s.namespace.name'] AS namespace,
       ResourceAttributes['k8s.pod.name'] AS pod,
       round(argMax(Value, TimeUnix) / 1048576, 1) AS memory_mib
FROM otel.otel_metrics_gauge
WHERE MetricName = 'k8s.pod.memory.working_set' AND TimeUnix > now() - INTERVAL 5 MINUTE
GROUP BY namespace, pod
ORDER BY memory_mib DESC
LIMIT 10;
