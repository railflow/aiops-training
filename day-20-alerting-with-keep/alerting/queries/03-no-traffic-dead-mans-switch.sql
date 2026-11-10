-- Alert: "dead man's switch". Silence is also a failure: if no spans AND no logs arrive, either the
-- service is down or the telemetry pipeline is broken. Always returns one row.
SELECT
  (SELECT count() FROM otel.otel_traces WHERE Timestamp > now() - INTERVAL 5 MINUTE AND ServiceName = 'shop-frontend') AS spans_5m,
  (SELECT count() FROM otel.otel_logs   WHERE Timestamp > now() - INTERVAL 5 MINUTE AND ServiceName = 'shop-frontend') AS logs_5m;
