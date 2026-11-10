-- All spans of one trace, in time order. Use --param_trace_id as in 04.
SELECT Timestamp, ServiceName, SpanName, SpanKind, SpanId, ParentSpanId, round(Duration / 1e6, 1) AS ms, StatusCode
FROM otel.otel_traces
WHERE TraceId = {trace_id:String}
ORDER BY Timestamp;
