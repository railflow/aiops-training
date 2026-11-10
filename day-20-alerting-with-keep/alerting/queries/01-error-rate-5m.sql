-- Alert: high error rate. Percentage of failed server spans in the last 5 minutes for the user-facing service
-- (symptom-based: shop-frontend returns an error when shop-backend fails).
-- Verify first: SELECT DISTINCT SpanKind, StatusCode FROM otel.otel_traces   (spelling varies by exporter version)
-- Always returns exactly one row. error_pct is 0 when there are fewer than 20 requests: too little traffic to judge.
SELECT 'shop-frontend' AS service,
       count() AS requests,
       if(count() < 20, 0, round(100 * countIf(StatusCode IN ('Error', 'STATUS_CODE_ERROR')) / count(), 2)) AS error_pct
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 5 MINUTE
  AND SpanKind IN ('Server', 'SPAN_KIND_SERVER')
  AND ServiceName = 'shop-frontend';
