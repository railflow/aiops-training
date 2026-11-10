-- Alert: containers restarting. The restart counter only goes up, so max - min inside the window is
-- "restarts in the window". If query 01 of Day 18 shows the metric in otel_metrics_sum, change the table.
SELECT count() AS containers_restarting,
       sum(restarts) AS restarts,
       arrayStringConcat(groupArray(concat(namespace, '/', pod)), ', ') AS pods
FROM (
  SELECT ResourceAttributes['k8s.namespace.name'] AS namespace,
         ResourceAttributes['k8s.pod.name'] AS pod,
         max(Value) - min(Value) AS restarts
  FROM otel.otel_metrics_gauge
  WHERE MetricName = 'k8s.container.restarts' AND TimeUnix > now() - INTERVAL 15 MINUTE
    AND ResourceAttributes['k8s.namespace.name'] = 'apps'
  GROUP BY namespace, pod, ResourceAttributes['k8s.container.name']
  HAVING restarts > 0
);
