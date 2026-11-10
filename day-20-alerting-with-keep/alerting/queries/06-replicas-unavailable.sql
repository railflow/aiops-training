-- Alert: fewer replicas available than desired for a Deployment, using the latest value in the last 3 minutes.
SELECT count() AS deployments_short,
       arrayStringConcat(groupArray(concat(deployment, ' ', toString(available), '/', toString(desired))), ', ') AS detail
FROM (
  SELECT ResourceAttributes['k8s.deployment.name'] AS deployment,
         argMaxIf(Value, TimeUnix, MetricName = 'k8s.deployment.desired') AS desired,
         argMaxIf(Value, TimeUnix, MetricName = 'k8s.deployment.available') AS available
  FROM otel.otel_metrics_gauge
  WHERE MetricName IN ('k8s.deployment.desired', 'k8s.deployment.available')
    AND ResourceAttributes['k8s.namespace.name'] = 'apps'
    AND TimeUnix > now() - INTERVAL 3 MINUTE
  GROUP BY deployment
  HAVING available < desired
);
