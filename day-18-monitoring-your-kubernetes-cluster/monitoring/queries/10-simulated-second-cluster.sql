-- SIMULATION ONLY: copies the last 10 minutes of ai-ops-training metrics and labels the copy "heyjob-simulated-b",
-- to show what a second cluster looks like in the same table. It is not real data; delete it afterwards:
--   ALTER TABLE otel.otel_metrics_gauge DELETE WHERE ResourceAttributes['k8s.cluster.name'] = 'heyjob-simulated-b';
-- SELECT * REPLACE keeps every column the exporter created, whatever the version.
INSERT INTO otel.otel_metrics_gauge
SELECT * REPLACE (mapUpdate(ResourceAttributes, map('k8s.cluster.name', 'heyjob-simulated-b')) AS ResourceAttributes)
FROM otel.otel_metrics_gauge
WHERE ResourceAttributes['k8s.cluster.name'] = 'ai-ops-training' AND TimeUnix > now() - INTERVAL 10 MINUTE;
