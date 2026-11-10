-- Deployments where available replicas are below desired right now (latest sample each).
SELECT deployment, desired, available, desired - available AS missing
FROM (
    SELECT ResourceAttributes['k8s.namespace.name'] AS ns,
           ResourceAttributes['k8s.deployment.name'] AS deployment,
           argMaxIf(Value, TimeUnix, MetricName = 'k8s.deployment.desired') AS desired,
           argMaxIf(Value, TimeUnix, MetricName = 'k8s.deployment.available') AS available
    FROM otel.otel_metrics_gauge
    WHERE MetricName IN ('k8s.deployment.desired', 'k8s.deployment.available') AND TimeUnix > now() - INTERVAL 5 MINUTE
    GROUP BY ns, deployment
)
WHERE desired > available
ORDER BY missing DESC;
