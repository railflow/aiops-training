-- Alert: slow checkout. p95 duration (milliseconds) of the user-facing /checkout server span over the last 5 minutes.
-- shop-frontend is what users hit; when shop-backend is slow or failing, this is where users feel it.
-- Duration is stored in nanoseconds. Returns one row; p95_ms is 0 when there is too little traffic to judge.
SELECT 'shop-frontend' AS service,
       count() AS requests,
       if(count() < 20, 0, round(quantile(0.95)(Duration) / 1e6, 1)) AS p95_ms
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 5 MINUTE
  AND SpanKind IN ('Server', 'SPAN_KIND_SERVER')
  AND ServiceName = 'shop-frontend'
  AND SpanName LIKE '%/checkout%';
