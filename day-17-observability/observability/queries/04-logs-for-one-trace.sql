-- Every log line of one request. Run with a real id, for example:
--   clickhouse-client --param_trace_id=<32 hex chars> --queries-file 04-logs-for-one-trace.sql
SELECT Timestamp, ServiceName, SeverityText, Body
FROM otel.otel_logs
WHERE TraceId = {trace_id:String}
ORDER BY Timestamp;
