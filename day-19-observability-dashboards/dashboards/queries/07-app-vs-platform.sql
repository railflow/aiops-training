-- The "is it my app or the platform?" query: per minute, the app's p95 latency next to the CPU used by its pods.
-- If latency climbs while CPU is flat and low, suspect your code or a dependency. If CPU sits at its limit, suspect
-- throttling (a resources problem you own). Change the service and pod prefix for your app.
SELECT t.minute, t.p95_ms, c.cpu_cores
FROM (
    SELECT toStartOfMinute(Timestamp) AS minute, round(quantile(0.95)(Duration) / 1e6, 1) AS p95_ms
    FROM otel.otel_traces
    WHERE ServiceName = 'shop-frontend' AND SpanKind IN ('Server', 'SPAN_KIND_SERVER') AND Timestamp > now() - INTERVAL 30 MINUTE
    GROUP BY minute
) AS t
LEFT JOIN (
    SELECT toStartOfMinute(TimeUnix) AS minute, round(sum(Value), 3) AS cpu_cores
    FROM otel.otel_metrics_gauge
    WHERE MetricName = 'k8s.pod.cpu.usage' AND ResourceAttributes['k8s.pod.name'] LIKE 'shop-frontend%'
      AND TimeUnix > now() - INTERVAL 30 MINUTE
    GROUP BY minute
) AS c ON t.minute = c.minute
ORDER BY t.minute;
