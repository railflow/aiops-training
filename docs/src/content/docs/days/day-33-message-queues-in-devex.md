---
title: "Day 33: Message queues, and why they matter in DevEx"
description: "Files in day-33-message-queues-in-devex/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 33: Message queues, and why they matter in DevEx"
  order: 33
---

This page is the file-by-file guide to [`day-33-message-queues-in-devex/`](https://github.com/railflow/aiops-training/tree/main/day-33-message-queues-in-devex) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Put a message bus between your engineering tools. Pipelines as events, one front door for infrastructure requests, a strangler facade over the legacy mess, and five labs on NATS JetStream.

Homework for this day is in [`day-33-message-queues-in-devex/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-33-message-queues-in-devex/homework.md) and is repeated at the bottom of this page.

## What is in the folder

41 files. Paths below are relative to the repo root unless noted.

### day-33-message-queues-in-devex/mq-devex/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/.gitignore` | Files git should not track for this folder. |  |
| `mq-devex/README.md` | Document: mq-devex: message queues for engineering systems (Day 33) |  |

### day-33-message-queues-in-devex/mq-devex/k8s/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/k8s/00-namespace.yaml` | Kubernetes manifest defining Namespace `mq-devex`. |  |
| `mq-devex/k8s/deploy-worker.sh` | Publish the code as a ConfigMap and (re)deploy one worker. ./deploy-worker.sh uitest lab2-pipeline/uitest.py [args...] Render only (no cluster needed): RENDER_ONLY=1 ./deploy-worker.sh uitest lab2-pipeline/uitest.py | `day-33-message-queues-in-devex/mq-devex/k8s/deploy-worker.sh uitest lab2-pipeline/uitest.py` |
| `mq-devex/k8s/worker.yaml.tpl` | One consumer = one tiny Deployment. Rendered by deploy-worker.sh (name, script, args, extra env). Code comes from the ConfigMap mq-devex-code. |  |

### day-33-message-queues-in-devex/mq-devex/lab1-bus-basics/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lab1-bus-basics/README.md` | Document: Lab 1: bus basics with the nats CLI |  |
| `mq-devex/lab1-bus-basics/captured-output.txt` | Text file (sample data or captured output). |  |
| `mq-devex/lab1-bus-basics/lab1.sh` | Lab 1: bus basics with the nats CLI. Needs: `nats` (natscli) and a NATS server with JetStream, reachable at $NATS_URL. NATS_URL=nats://127.0.0.1:4222 ./lab1.sh (local nats-server, or `kubectl port-forward -n data svc/nats 4222:4222`) |  |

### day-33-message-queues-in-devex/mq-devex/lab2-pipeline/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lab2-pipeline/README.md` | Document: Lab 2: the pipeline as events |  |
| `mq-devex/lab2-pipeline/audit_sink.py` | Audit sink: a durable consumer of EVERYTHING in the stream, writing one row per event to JSONL and/or ClickHouse (table bus.events, sql/001_bus_events.sql). | `python uitest.py` (then: loadtest.py, gate.py, deploy.py, notify.py, audit_sink.py) |
| `mq-devex/lab2-pipeline/captured-trace.txt` | Captured live 2026-11-05: nats-server 2.11.17, Python 3.12, all six workers as separate processes, one 'emit_build.py' run. Columns: time, worker that handled the event, event type, events that worker published in response. |  |
| `mq-devex/lab2-pipeline/deploy.py` | Deploy stage: reacts to ci.gate.passed only. The stand-in "deploys" by emitting ci.deploy.completed (a real one would call Argo CD / Flux, Day 8). |  |
| `mq-devex/lab2-pipeline/emit_build.py` | Pretend to be the build job: publish ci.build.completed. Everything downstream reacts; this script knows nobody. | `python emit_build.py --repo orders-api --sha 4f2a9c1` |
| `mq-devex/lab2-pipeline/gate.py` | The join. Choreography has no conductor, so "wait for both test stages" becomes state YOU own: |  |
| `mq-devex/lab2-pipeline/loadtest.py` | Load-test stage (Python stand-in; loadtest_consumer.go.txt shows the same consumer in Go). Runs in parallel with uitest: nobody told either of them about the other. | `python uitest.py` (then: loadtest.py, gate.py, deploy.py, notify.py, audit_sink.py) |
| `mq-devex/lab2-pipeline/loadtest_consumer.go.txt` | Text file (sample data or captured output). |  |
| `mq-devex/lab2-pipeline/notify.py` | Notifier: tells humans about the two outcomes that matter. It subscribes to ci.&gt; and ignores the rest, which is how you add a new listener without touching any other worker. |  |
| `mq-devex/lab2-pipeline/uitest.py` | UI-test stage. Listens for ci.build.completed, pretends to run UI tests, announces ci.test.uitest.completed. |  |

### day-33-message-queues-in-devex/mq-devex/lab3-infra-router/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lab3-infra-router/README.md` | Document: Lab 3: the infra request router |  |
| `mq-devex/lab3-infra-router/human_desk.py` | Handles infra.approval.&lt;id&gt; and infra.completion.&lt;id&gt;. | `python router.py & python terraform_runner.py & python human_desk.py &` |
| `mq-devex/lab3-infra-router/router.py` | Pure function: request data in, decision out. This is the part you unit-test; there is no NATS in it. |  |
| `mq-devex/lab3-infra-router/routes.yaml` | Routing rules for infrastructure requests. Evaluated top to bottom; first match wins. |  |
| `mq-devex/lab3-infra-router/terraform_runner.py` | The automation path. STAND-IN: it simulates "terraform plan, terraform apply" and invents outputs. | `python router.py & python terraform_runner.py & python human_desk.py &` |

### day-33-message-queues-in-devex/mq-devex/lab4-strangler/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lab4-strangler/README.md` | Document: Lab 4: the strangler facade |  |
| `mq-devex/lab4-strangler/adapters.py` | Two adapters behind the facade. Both end by publishing the SAME event, ci.completed, with an `impl` field. That sameness is the whole point: consumers of ci.completed cannot tell (and should not need to know) which implementation ran. | `NEW_BUG=1 python adapters.py new` (restart the new adapter with a bug: shadow mode catches it before any real traffic moves) |
| `mq-devex/lab4-strangler/compare.py` | Shadow-mode judge: when a correlation id has a ci.completed from BOTH implementations, publish ci.compare.result &#123;agree: | `nats kv put flags ci-runner shadow` (both run; compare.py says agree true or false) |
| `mq-devex/lab4-strangler/facade.py` | Pure function: which implementations run, and is each one a shadow? -&gt; [(impl, shadow)] |  |
| `mq-devex/lab4-strangler/legacy/run_ci_legacy.sh` | THE LEGACY THING. Pretend this is the old CI system's trigger: |  |

### day-33-message-queues-in-devex/mq-devex/lab5-bridges/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lab5-bridges/README.md` | Document: Lab 5 (optional): webhooks onto the bus |  |
| `mq-devex/lab5-bridges/bridge.py` | Webhook-to-bus bridge: the ONLY place that knows about vendor payload shapes. Everything behind it sees one envelope. |  |
| `mq-devex/lab5-bridges/serve.py` | Run the bridge: python3 serve.py (listens on 0.0.0.0:8080; needs fastapi and uvicorn: |  |

### day-33-message-queues-in-devex/mq-devex/lib/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/lib/devbus.py` | devbus.py: the small shared library every lab uses. One envelope, one worker loop, one place where retries, DLQ and idempotency live. |  |
| `mq-devex/lib/platform_request.py` | `platform request ...`: the front door for infrastructure requests, backed by the bus. Called by day-10-local-platform/platform/platform. |  |

### day-33-message-queues-in-devex/mq-devex/sql/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/sql/001_bus_events.sql` | Day 33: every event on the bus, one immutable row each. Written by lab2-pipeline/audit_sink.py. Matches the style of the Day 13/capstone tables. |  |
| `mq-devex/sql/queries.sql` | name: trace_by_correlation Everything that happened for ONE business story, in order, with who caused what. |  |

### day-33-message-queues-in-devex/mq-devex/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `mq-devex/tests/conftest.py` | Shared fixtures: a REAL nats-server with JetStream, started fresh for every test (about 0.3 s), so no test sees another's messages. |  |
| `mq-devex/tests/test_bridges.py` | Lab 5: webhook bridges. Pure mapping + signature tests, plus one run through a real nats-server. |  |
| `mq-devex/tests/test_infra_router.py` | Lab 3: the routing rules (pure), then the whole path through the REAL `./platform request` CLI against a real nats-server. |  |
| `mq-devex/tests/test_pipeline.py` | Lab 2 against a real nats-server: the pipeline as events, the correlation chain, redelivery after a killed consumer, idempotency, DLQ. |  |
| `mq-devex/tests/test_sql.py` | The bus_events DDL and every named query, run against embedded ClickHouse (chdb) with seeded rows. Skips without chdb. chdb bundles a newer ClickHouse than the course's 24.8; re-run against your server. |  |
| `mq-devex/tests/test_strangler.py` | Lab 4: the strangler facade. Flip the flag at runtime and watch traffic move, with no redeploy and no change to the caller. |  |

## Files this day uses from other folders

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`data/`).

From [Day 10](/days/day-10-local-platform/): `day-10-local-platform/` (`platform/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-33-message-queues-in-devex/mq-devex
python3 -m venv .venv && . .venv/bin/activate
pip install nats-py==2.16.0 pyyaml fastapi uvicorn httpx pytest chdb
export NATS_URL=nats://127.0.0.1:4222
export PYTHONPATH="$PWD/lib:$PWD/lab2-pipeline:$PWD/lab3-infra-router:$PWD/lab4-strangler:$PWD/lab5-bridges"
nats server check connection
```

```bash
cd day-33-message-queues-in-devex/mq-devex/lab2-pipeline
for w in uitest loadtest gate deploy notify audit_sink; do python $w.py 2> /tmp/$w.log & done
```

```bash
day-33-message-queues-in-devex/mq-devex/k8s/deploy-worker.sh uitest lab2-pipeline/uitest.py
EXTRA="UITEST_SECONDS=20 ACK_WAIT=15" day-33-message-queues-in-devex/mq-devex/k8s/deploy-worker.sh uitest lab2-pipeline/uitest.py
kubectl -n mq-devex logs -f deploy/uitest
```

```bash
cd day-33-message-queues-in-devex/mq-devex/lab3-infra-router
python router.py & python terraform_runner.py & python human_desk.py &
cd ../../platform
./platform request kinds
./platform request k8s-namespace-rds --name orders --owner alice --env dev --wait
./platform request k8s-namespace-rds --name orders --owner alice --env prod --id req-1 --wait
./platform request approve req-1 --by bob
./platform request status req-1
./platform request aws-account --name sandbox-7 --owner carol --id req-2
./platform request complete req-2 --by dana
./platform request teleporter --name x --owner a --wait
```

```bash
git add day-33-message-queues-in-devex/mq-devex docs
git commit -m "Add my message contracts and routes for <your handoffs>"
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
OK Connection OK:connected to nats://127.0.0.1:4222 in 1.3ms OK:rtt time 143µs OK:round trip took 0.000576s
```

```text
request req-1 submitted (k8s-namespace-rds). Check it: platform request status req-1
2026-11-05T12:50:01.114Z  waiting-on-human   {"route": "namespace-with-database-prod", "team": "platform-oncall", "sla_minutes": 240}
waiting on a human; this command stops waiting. Re-check with: platform request status req-1
...
2026-11-05T12:51:09.870Z  approved           {"by": "bob"}
2026-11-05T12:51:10.402Z  done               {"by": "automation", "outputs": {"namespace": "orders-prod", ...}}
```

## How these files relate to other days and shared tools

- Builds on [Day 4](/days/day-04-data-services-and-appwrite/), [Day 17](/days/day-17-observability/), [Day 19](/days/day-19-observability-dashboards/), [Day 25](/days/day-25-internal-platform/), [Day 27](/days/day-27-durable-workflows-temporal/) (cluster, images or secrets created there).
- Uses [`tools/versions.env`](/tools/) (for example from `day-33-message-queues-in-devex/mq-devex/README.md`).
- Refers to files in [Day 4](/days/day-04-data-services-and-appwrite/) (for example from `day-33-message-queues-in-devex/mq-devex/README.md`).
- Refers to files in [Day 10](/days/day-10-local-platform/) (for example from `day-33-message-queues-in-devex/mq-devex/lab3-infra-router/README.md`).
- Files from this folder are used by [Day 10](/days/day-10-local-platform/).

## Homework

**Pick one of these and time-box it to a couple of hours:**

1. **Your company's mess.** Choose two handoffs between teams that go through tickets or chat today (for example "new repo", "new test environment", "rotate a certificate"). For each, write the message contract: subject, envelope, payload schema, who publishes, who consumes, the failure paths. Draw it as a Mermaid diagram.
2. **Extend Lab 3.** Add one new request kind (for example `dns-record` to a human, `test-environment` to automation) to `routes.yaml`, with a test, and show it end to end with `./platform request`.
3. **Extend the capstone.** Replace the capstone's webhook receiver with a bus consumer that starts the same Temporal workflows, with the workflow id derived from the event id. Explain what you gain and what you lose.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Contracts** | Free-form text | Subjects, envelope and payload written down | Versioned schema (AsyncAPI or JSON Schema) with a compatibility rule |
| **Failure handling** | Happy path only | Retries and a dead-letter path | Idempotency argued per consumer, poison and ordering cases covered, a runbook |
| **Observability** | "We would log it" | Correlation id and one query | A dashboard or alert on queue age and time-in-state, with a threshold justified |
| **Honesty** | Everything "just works" | Names one trade-off | States when **not** to use a bus for this case, and what the cheaper alternative is |
| **Evidence** | Claims only | A test or captured run | Tests plus a failure injected on purpose |

### Ask AI (use it as a reviewer, not an author)

- "Here is my message contract. Which consumer would break if I add a required field? Which if I rename one?"
- "Here is my handler. Under at-least-once delivery, list every way it could double-apply an effect."
- "Argue the case **against** putting a message bus in this design. What is the simplest alternative?"
- "Given this routes.yaml, write five requests that fall through the rules in surprising ways."

Check anything it says against the NATS or CloudEvents documentation before you believe it.
