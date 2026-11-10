# Lab 2: the pipeline as events

```
emit_build.py  --ci.build.completed-->  uitest.py   --ci.test.uitest.completed-->  gate.py --ci.gate.passed--> deploy.py --ci.deploy.completed--> notify.py
                                        loadtest.py --ci.test.loadtest.completed-->        \--ci.gate.failed----------------------------------------> notify.py
                                                                         audit_sink.py listens to everything (JSONL and/or ClickHouse bus.events)
```

Each file is a stand-alone consumer. They only share the subject names and the envelope in `../lib/devbus.py`.

## Run it on your laptop (one terminal per worker, or `&`)

```bash
export PYTHONPATH=../lib NATS_URL=nats://127.0.0.1:4222 STATE_DIR=.state
python3 uitest.py & python3 loadtest.py & python3 gate.py & python3 deploy.py & python3 notify.py & python3 audit_sink.py &
python3 emit_build.py --repo orders-api --sha 4f2a9c1          # prints correlationid=...
python3 emit_build.py --repo orders-api --sha bad0001 --fail-ui   # gate fails, notify says BLOCKED, deploy never runs
cat .state/notifications.jsonl .state/events.jsonl
```

Windows PowerShell: `$env:PYTHONPATH="..\lib"; $env:NATS_URL="nats://127.0.0.1:4222"; Start-Process python uitest.py` (one `Start-Process` per worker), same for the rest.

Worker logs are one JSON object per line on stderr, each carrying `correlationid`. `grep <correlationid>` across the terminals reconstructs the story.

## Kill a consumer mid-chain

```bash
UITEST_SECONDS=20 ACK_WAIT=10 python3 uitest.py          # slow tests, short ack wait
python3 emit_build.py --repo orders-api --sha kill001
# while uitest is "testing": Ctrl-C it. Start it again (same command). After <= 10 s the message is redelivered ("delivered": 2 in its log).
```

The test `tests/test_pipeline.py::test_killed_consumer_means_redelivery` does the same thing in code.

## On kind

```bash
../k8s/deploy-worker.sh uitest lab2-pipeline/uitest.py        # repeat for loadtest, gate, deploy, notify, audit_sink
kubectl -n mq-devex logs -f deploy/uitest
```

`EXTRA="UITEST_SECONDS=20 ACK_WAIT=15" ../k8s/deploy-worker.sh ...` sets pod env. Then `kubectl -n mq-devex delete pod -l app=uitest` mid-test to kill it. (Not run on a cluster here; see the main README.)

## ClickHouse

Apply `../sql/001_bus_events.sql`, set `CLICKHOUSE_URL`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD` for `audit_sink.py` (from a Secret), then run the named queries in `../sql/queries.sql`
(`trace_by_correlation`, `pipeline_lead_time`, `dead_letters`, `stuck_runs`). The SQL runs against embedded ClickHouse in `tests/test_sql.py`; the HTTP insert in `audit_sink.py` was not run against a live server.

## Idempotency, three layers

1. `devbus.Seen`: a redelivered event id is acked without running the handler.
2. Deterministic output ids (`derived_id`) plus `Nats-Msg-Id`: if a worker crashes after publishing but before marking done, the re-run publishes the same id and the stream drops it.
3. `gate.py` stores results by (correlation id, kind) with INSERT OR REPLACE, so a replay of the same result is harmless.
