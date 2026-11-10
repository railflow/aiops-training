-- name: trace_by_correlation
-- Everything that happened for ONE business story, in order, with who caused what.
SELECT event_time, type, source, event_id, causation_id
FROM bus.events
WHERE correlation_id = {cid:String}
ORDER BY event_time, event_id;

-- name: pipeline_lead_time
-- Build finished -> deployed, per correlation id, only for runs that reached deploy.
SELECT
    correlation_id,
    minIf(event_time, type = 'ci.build.completed')  AS built_at,
    maxIf(event_time, type = 'ci.deploy.completed') AS deployed_at,
    dateDiff('millisecond', built_at, deployed_at)   AS lead_ms
FROM bus.events
GROUP BY correlation_id
HAVING deployed_at > toDateTime64(0, 3, 'UTC')
ORDER BY built_at;

-- name: events_per_type
SELECT type, count() AS n FROM bus.events GROUP BY type ORDER BY n DESC;

-- name: dead_letters
-- Anything that landed in a dead-letter subject. This number should be zero or a ticket.
SELECT correlation_id, JSONExtractString(data, 'worker') AS worker, JSONExtractString(data, 'reason') AS reason
FROM bus.events
WHERE type = 'devex.dlq.entry'
ORDER BY event_time;

-- name: stuck_runs
-- Builds that never reached a gate verdict within 10 minutes: the "where did it go?" query.
SELECT correlation_id, min(event_time) AS started
FROM bus.events
GROUP BY correlation_id
HAVING countIf(type IN ('ci.gate.passed', 'ci.gate.failed')) = 0
   AND countIf(type = 'ci.build.completed') > 0
   AND started < now() - INTERVAL 10 MINUTE;

-- name: shadow_agreement
-- Lab 4: how often did the new CI implementation agree with the legacy one while both ran?
SELECT
    countIf(JSONExtractBool(data, 'agree'))  AS agreed,
    countIf(NOT JSONExtractBool(data, 'agree')) AS disagreed,
    round(agreed / (agreed + disagreed) * 100, 1) AS agreement_pct
FROM bus.events
WHERE type = 'ci.compare.result';

-- name: impl_mix
-- Lab 4: how much real (non-shadow) traffic does each implementation serve, and how fast?
SELECT
    JSONExtractString(data, 'impl') AS impl,
    count() AS runs,
    round(avg(JSONExtractUInt(data, 'duration_ms'))) AS avg_ms
FROM bus.events
WHERE type = 'ci.completed' AND NOT JSONExtractBool(data, 'shadow')
GROUP BY impl
ORDER BY runs DESC;
