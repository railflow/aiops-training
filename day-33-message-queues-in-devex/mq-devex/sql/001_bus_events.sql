-- Day 33: every event on the bus, one immutable row each. Written by lab2-pipeline/audit_sink.py. Matches the style of the Day 13/capstone tables.
CREATE DATABASE IF NOT EXISTS bus;

CREATE TABLE IF NOT EXISTS bus.events
(
    event_time     DateTime64(3, 'UTC'),
    event_id       String,
    correlation_id String,
    causation_id   String,
    type           LowCardinality(String),
    source         LowCardinality(String),
    entity         String,          -- the CloudEvents `subject`: what the event is about, e.g. orders-api@4f2a9c1
    data           String           -- the event payload as JSON text; use JSONExtract* to read it
)
ENGINE = MergeTree
ORDER BY (correlation_id, event_time)
TTL toDateTime(event_time) + INTERVAL 90 DAY;
