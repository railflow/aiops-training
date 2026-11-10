-- Top 5 pods by CPU over the last 15 minutes: average and p95-ish (95th percentile of the samples).
SELECT ResourceAttributes['k8s.namespace.name'] AS namespace,
       ResourceAttributes['k8s.pod.name'] AS pod,
       round(avg(Value), 3) AS avg_cores,
       round(quantile(0.95)(Value), 3) AS p95_cores
FROM otel.otel_metrics_gauge
WHERE MetricName = 'k8s.pod.cpu.usage' AND TimeUnix > now() - INTERVAL 15 MINUTE
GROUP BY namespace, pod
ORDER BY p95_cores DESC
LIMIT 5;
