# mq-devex: message queues for engineering systems (Day 33)

Five labs that put a message bus between the tools you already have. The lesson text is on the course site.

| Lab | Folder | What you build | Needs |
| --- | --- | --- | --- |
| 1 | `lab1-bus-basics/` | A stream, a durable consumer, ack, replay, dedupe, with the `nats` CLI | `nats` CLI + a NATS server with JetStream |
| 2 | `lab2-pipeline/` | build -> UI tests + load test -> gate -> deploy -> notify, as events; trace it by correlation id; kill a worker | Lab 1 + Python 3.10+ |
| 3 | `lab3-infra-router/` | `infra.request.>` router with YAML rules, automation and human paths, `./platform request` CLI | Lab 2 |
| 4 | `lab4-strangler/` | Facade in front of a legacy CI trigger, flag-driven rollout, shadow comparison | Lab 2 |
| 5 | `lab5-bridges/` (optional) | Forgejo, Keep and Gatus webhooks become bus events | Lab 2 |

Shared code: `lib/devbus.py` (the envelope, the worker loop with ack/retry/DLQ/idempotency), `lib/platform_request.py` (the CLI behind `./platform request`).
ClickHouse: `sql/001_bus_events.sql` and `sql/queries.sql`. Kubernetes: `k8s/` (one Deployment per consumer).

## Get the tools without installing anything system-wide

macOS or Linux (the course pins `nats:2.11-alpine`, so use a 2.11 server; the labs were verified with the versions in `../../tools/versions.env`):

```bash
mkdir -p ~/mq-tools && cd ~/mq-tools
# nats-server: pick the archive for your OS/CPU from https://github.com/nats-io/nats-server/releases (look for v2.11.x), then:
tar xzf nats-server-v2.11.17-darwin-arm64.tar.gz && mv nats-server-*/nats-server .
# nats CLI: https://github.com/nats-io/natscli/releases (zip), then:
unzip nats-0.5.1-darwin-arm64.zip && mv nats-*/nats .
export PATH="$PWD:$PATH"
nats-server -js -sd ./js-data -a 127.0.0.1 -p 4222     # leave running in its own terminal
```

Windows (PowerShell): download the `windows-amd64` zip files from the same release pages, unzip them into `$HOME\mq-tools`, then `$env:Path += ";$HOME\mq-tools"` and run `nats-server.exe -js -sd .\js-data -a 127.0.0.1 -p 4222`.

Or skip local binaries and use the Day 4 deployment: `kubectl apply -f day-04-data-services-and-appwrite/data/nats.yaml`, then `kubectl -n data port-forward svc/nats 4222:4222`.
(That manifest still says `nats:2.10-alpine` while `versions.env` pins 2.11; the commands used here exist in both, but only 2.11.17 was run.)

Python (project-local virtualenv, nothing system-wide):

```bash
python3 -m venv .venv && . .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install nats-py==2.16.0 pyyaml fastapi uvicorn httpx pytest chdb
export PYTHONPATH="$PWD/lib:$PWD/lab2-pipeline:$PWD/lab3-infra-router:$PWD/lab4-strangler:$PWD/lab5-bridges"
export NATS_URL=nats://127.0.0.1:4222
```

## Run the tests

The tests start a real `nats-server` per test (about 0.3 s each). They skip if no binary is found.

```bash
NATS_SERVER_BIN=$(which nats-server) python -m pytest tests -q
```

Last run: 40 tests across pipeline, router + CLI, strangler, bridges and ClickHouse SQL (see "What was verified" in the course page).

## What is NOT verified here

- Nothing was run on a Kubernetes cluster: `k8s/` was rendered and parsed as YAML only.
- The Go consumer in `lab2-pipeline/loadtest_consumer.go.txt` was not compiled (Go was not available).
- The Slack/Jira notifier is a file sink; `NOTIFY_WEBHOOK` was not run against a real webhook.
- The Forgejo issue creation in `lab3-infra-router/human_desk.py` was not run (no Forgejo); the "Terraform" is a stand-in.
- The Keep webhook payload shape is an assumption; the Gatus body uses placeholders verified in Gatus's README but was not run through Gatus.
