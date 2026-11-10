-- Who calls whom: join each span to its parent span in the same trace.
SELECT p.ServiceName AS caller, c.ServiceName AS callee, count() AS calls,
       round(quantile(0.95)(c.Duration) / 1e6, 1) AS callee_p95_ms
FROM otel.otel_traces AS c
INNER JOIN otel.otel_traces AS p ON c.TraceId = p.TraceId AND c.ParentSpanId = p.SpanId
WHERE c.Timestamp > now() - INTERVAL 30 MINUTE AND p.Timestamp > now() - INTERVAL 30 MINUTE
  AND p.ServiceName != c.ServiceName
GROUP BY caller, callee
ORDER BY calls DESC;
