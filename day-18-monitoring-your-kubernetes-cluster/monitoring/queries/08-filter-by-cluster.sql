-- Every cluster that is sending data, and how fresh it is. With one cluster you see one row;
-- with hundreds, this is how you notice one went quiet.
SELECT ResourceAttributes['k8s.cluster.name'] AS cluster,
       count() AS points_last_hour,
       max(TimeUnix) AS last_seen
FROM otel.otel_metrics_gauge
WHERE TimeUnix > now() - INTERVAL 1 HOUR
GROUP BY cluster
ORDER BY last_seen DESC;
