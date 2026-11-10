-- Alert: a pod is using more than 90% of its memory limit (an OOMKill is likely soon).
SELECT count() AS pods_hot,
       arrayStringConcat(groupArray(concat(pod, ' ', toString(pct), '%')), ', ') AS detail
FROM (
  SELECT m.pod AS pod, round(100 * m.mem / l.lim, 1) AS pct
  FROM (SELECT ResourceAttributes['k8s.pod.name'] AS pod, argMax(Value, TimeUnix) AS mem
        FROM otel.otel_metrics_gauge
        WHERE MetricName = 'k8s.pod.memory.working_set' AND TimeUnix > now() - INTERVAL 3 MINUTE
          AND ResourceAttributes['k8s.namespace.name'] = 'apps'
        GROUP BY pod) AS m
  INNER JOIN (SELECT ResourceAttributes['k8s.pod.name'] AS pod, sum(Value) AS lim
              FROM otel.otel_metrics_gauge
              WHERE MetricName = 'k8s.container.memory_limit' AND TimeUnix > now() - INTERVAL 3 MINUTE
              GROUP BY pod) AS l ON m.pod = l.pod
  WHERE l.lim > 0 AND m.mem / l.lim > 0.90
);
