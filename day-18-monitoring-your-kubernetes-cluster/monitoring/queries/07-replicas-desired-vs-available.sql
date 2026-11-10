-- Deployment replicas, desired versus available, per minute (from the k8s_cluster receiver).
SELECT toStartOfMinute(TimeUnix) AS minute,
       ResourceAttributes['k8s.deployment.name'] AS deployment,
       MetricName,
       max(Value) AS replicas
FROM otel.otel_metrics_gauge
WHERE MetricName IN ('k8s.deployment.desired', 'k8s.deployment.available')
  AND ResourceAttributes['k8s.namespace.name'] = 'apps'
  AND TimeUnix > now() - INTERVAL 30 MINUTE
GROUP BY minute, deployment, MetricName
ORDER BY deployment, minute, MetricName;
