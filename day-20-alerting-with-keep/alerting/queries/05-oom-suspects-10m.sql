-- Alert: probable OOMKill. The metrics here do not carry the termination reason, so this is a PROXY:
-- a container restarted in the last 10 minutes AND its pod's memory working set was above 85% of its
-- limit in the 5 minutes before. Confirm with: kubectl -n apps describe pod <pod> (Last State: OOMKilled).
-- (The k8s_cluster receiver may offer an optional last-terminated-reason metric: check its documentation.)
SELECT count() AS suspects, arrayStringConcat(groupArray(pod), ', ') AS pods
FROM (
  SELECT r.pod AS pod
  FROM (SELECT ResourceAttributes['k8s.pod.name'] AS pod, max(Value) - min(Value) AS restarts
        FROM otel.otel_metrics_gauge
        WHERE MetricName = 'k8s.container.restarts' AND TimeUnix > now() - INTERVAL 10 MINUTE
        GROUP BY pod HAVING restarts > 0) AS r
  INNER JOIN (SELECT ResourceAttributes['k8s.pod.name'] AS pod, max(Value) AS mem
              FROM otel.otel_metrics_gauge
              WHERE MetricName = 'k8s.pod.memory.working_set' AND TimeUnix > now() - INTERVAL 15 MINUTE
              GROUP BY pod) AS m ON r.pod = m.pod
  INNER JOIN (SELECT ResourceAttributes['k8s.pod.name'] AS pod, sum(Value) AS lim
              FROM otel.otel_metrics_gauge
              WHERE MetricName = 'k8s.container.memory_limit' AND TimeUnix > now() - INTERVAL 15 MINUTE
              GROUP BY pod) AS l ON r.pod = l.pod
  WHERE l.lim > 0 AND m.mem / l.lim > 0.85
);
