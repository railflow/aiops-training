-- Which StatusCode strings exist in YOUR data? (Spelling differs between exporter versions.)
SELECT DISTINCT StatusCode FROM otel.otel_traces;
-- Then count the failing ones per service (adjust the string if needed).
SELECT ServiceName, SpanName, count() AS failed
FROM otel.otel_traces
WHERE Timestamp > now() - INTERVAL 15 MINUTE AND StatusCode IN ('Error', 'STATUS_CODE_ERROR')
GROUP BY ServiceName, SpanName
ORDER BY failed DESC;
