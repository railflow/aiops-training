-- Alert: the synthetic load (k6) is not arriving. Requests whose user agent starts with "k6" in the last 5 minutes.
-- The attribute name depends on the instrumentation version, so check first which one your spans use:
--   SELECT DISTINCT arrayJoin(mapKeys(SpanAttributes)) FROM otel.otel_traces WHERE ServiceName = 'shop-frontend' LIMIT 50;
SELECT count() AS k6_requests_5m
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 5 MINUTE
  AND SpanKind IN ('Server', 'SPAN_KIND_SERVER')
  AND ServiceName = 'shop-frontend'
  AND (SpanAttributes['http.user_agent'] LIKE 'k6%' OR SpanAttributes['user_agent.original'] LIKE 'k6%');
