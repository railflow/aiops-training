---
title: "Day 27: Durable workflows with Temporal"
description: "Files in day-27-durable-workflows-temporal/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 27: Durable workflows with Temporal"
  order: 27
---

This page is the file-by-file guide to [`day-27-durable-workflows-temporal/`](https://github.com/railflow/aiops-training/tree/main/day-27-durable-workflows-temporal) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Stop restarting three-day scripts from step 1. Learn what durable execution is, how Temporal differs from CI, install it on kind, build a resumable workflow in Python, and dispatch it from CI without ever blocking a runner.

Homework for this day is in [`day-27-durable-workflows-temporal/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-27-durable-workflows-temporal/homework.md) and is repeated at the bottom of this page.

## What is in the folder

30 files. Paths below are relative to the repo root unless noted.

### day-27-durable-workflows-temporal/temporal/.forgejo/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/.forgejo/workflows/dispatch.yaml` | CI verifies and packages, then FIRES the long-running workflow and exits. |  |

### day-27-durable-workflows-temporal/temporal/bad-script/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/bad-script/.gitignore` | Files git should not track for this folder. |  |
| `temporal/bad-script/README.md` | Document: bad-script: what not to build |  |
| `temporal/bad-script/month_end.py` | A month-end batch the way it is usually written. DO NOT COPY THIS PATTERN. | `python month_end.py BATCH-2026-11` (press Ctrl+C when you see "sent to customer-3") |

### day-27-durable-workflows-temporal/temporal/helm/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/helm/values-kind.yaml` | Temporal on the course's kind cluster, a SMALL install. Chart: | `-f day-27-durable-workflows-temporal/temporal/helm/values-kind.yaml --wait --timeout 10m` |

### day-27-durable-workflows-temporal/temporal/input/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/input/batch-2026-11.json` | JSON data or configuration file. |  |

### day-27-durable-workflows-temporal/temporal/k8s/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/k8s/devserver.yaml` | DEV ONLY: the Temporal CLI's built-in dev server (in-memory unless you add --db-filename and a volume) as a single pod. One process, no Postgres, state lost when the pod restarts. Great for the concept lab, wrong for anything you care about. Defines: Namespace, Deployment, Service. | `kubectl apply -f day-27-durable-workflows-temporal/temporal/k8s/devserver.yaml` |
| `temporal/k8s/ingressroute-ui.yaml` | Web UI at http://temporal.localhost:8080 (the chart's Service is temporal-web:8080). The UI can read and TERMINATE workflows: on anything but a laptop put the forward-auth middleware from Day 7 in front of it. Defines: IngressRoute `temporal-ui`. | `kubectl apply -f day-27-durable-workflows-temporal/temporal/k8s/ingressroute-ui.yaml` |
| `temporal/k8s/namespace.yaml` | Kubernetes manifest defining Namespace `temporal-apps`. |  |
| `temporal/k8s/worker-deployment.yaml` | Two workers of the Python MonthlyTaxProcessingWorkflow. Workers make OUTBOUND gRPC calls only: |  |

### day-27-durable-workflows-temporal/temporal/multicluster/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/multicluster/app-foo-link.yaml.tpl` | Applied to the "app-foo" cluster after replacing __COMMON_NODE_IP__ (see probe.sh). |  |
| `temporal/multicluster/common-postgres.yaml` | Applied to the "common" cluster: kubectl --context kind-common apply -f common-postgres.yaml A throwaway Postgres for the proof. The password is a demo value for a laptop-only database: real shared services use Secrets (Day 16). Defines: Namespace, Deployment, Service. |  |
| `temporal/multicluster/kind-app-foo.yaml` | kind create cluster --config kind-app-foo.yaml Defines: Cluster. |  |
| `temporal/multicluster/kind-common.yaml` | A SECOND and THIRD kind cluster, beside ai-ops-training. No host port mappings (8080/8443 are taken by ai-ops-training). Created with raw kind commands; the course's ./tools/kind wrapper only manages ai-ops-training and is unchanged. Defines: Cluster. |  |
| `temporal/multicluster/probe.sh` | Two clusters, one Docker network, one proof. Needs docker, kind, kubectl (you install them; this script installs nothing). |  |

### day-27-durable-workflows-temporal/temporal/python/

| File | What it is | How the lesson uses it |
|---|---|---|
| `temporal/python/.dockerignore` | Files kept out of the Docker build context. |  |
| `temporal/python/.gitignore` | Files git should not track for this folder. |  |
| `temporal/python/Dockerfile` | Temporal worker image. Pinned by tag AND digest; the digest was read on 2026-11-05 and WILL be stale: refresh it (Day 24). |  |
| `temporal/python/activities.py` | Activities: the code that touches the outside world. Anything that can fail, take a long time, or have a side effect goes here. |  |
| `temporal/python/models.py` | Plain data classes shared by the workflow, activities, starter and tests. |  |
| `temporal/python/pytest.ini` | pytest settings for this folder. |  |
| `temporal/python/replay.py` | Replay a recorded history against the CURRENT workflow code. If you changed the code in a way that breaks running workflows, this raises a non-determinism error here, in a test or CI step, instead of in production. |  |
| `temporal/python/requirements-dev.txt` | Pinned Python dependencies for this folder. | `pip install -r requirements-dev.txt` |
| `temporal/python/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `temporal/python/starter.py` | Start (or find) a MonthlyTaxProcessingWorkflow from code. Same job as the CLI, with typed input. |  |
| `temporal/python/worker.py` | The worker: YOUR process. It polls a task queue and runs workflow and activity code. Run 2+ of them; any can pick up any task. |  |
| `temporal/python/workflow.py` | MonthlyTaxProcessingWorkflow: deterministic orchestration. Rules for this file: |  |
| `temporal/python/pitfalls/pitfalls.py` | Two ways to break determinism, on purpose. Pick the behaviour with the PITFALL environment variable: |  |
| `temporal/python/pitfalls/replay_pitfall.py` | Replay a recorded PitfallWorkflow history against the code selected by PITFALL. This is how you catch a breaking change BEFORE deploying. |  |
| `temporal/python/tests/test_workflow.py` | Workflow tests with the time-skipping test server: a 72-hour approval window runs in milliseconds. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```powershell
cd day-27-durable-workflows-temporal/temporal/bad-script
$env:STEP_SECONDS = "1"; $env:IRS_FAIL_RATE = "0"
python month_end.py BATCH-2026-11      # press Ctrl+C when you see "sent to customer-3"
```

```bash
cd day-27-durable-workflows-temporal/temporal/bad-script
STEP_SECONDS=1 IRS_FAIL_RATE=0 python3 month_end.py BATCH-2026-11   # press Ctrl+C (or kill -9) when you see "sent to customer-3"
```

```bash
kubectl apply -f day-27-durable-workflows-temporal/temporal/k8s/devserver.yaml
kubectl -n temporal-dev rollout status deploy/temporal-dev
kubectl -n temporal-dev port-forward svc/temporal-dev 7233:7233 8233:8233
```

```bash
helm repo add temporal https://go.temporal.io/helm-charts
helm repo update
helm show values temporal/temporal --version 1.8.0 | less        # read it: the datastores section explains every key
helm install temporal temporal/temporal --version 1.8.0 -n temporal \
-f day-27-durable-workflows-temporal/temporal/helm/values-kind.yaml --wait --timeout 10m
```

```bash
kubectl apply -f day-27-durable-workflows-temporal/temporal/k8s/ingressroute-ui.yaml
kubectl -n temporal port-forward svc/temporal-frontend 7233:7233        # leave running
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
state.json  : {"done": ["verify_records", "generate_pdfs", "check_irs"]}
outbox.log  : 3 lines (customers 1 to 3 were emailed)
```

```text
deployment "temporal-dev" successfully rolled out
Forwarding from 127.0.0.1:7233 -> 7233
Forwarding from 127.0.0.1:8233 -> 8233
```

## How these files relate to other days and shared tools

- Builds on [Day 5](/days/day-05-kubernetes-jobs/), [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 17](/days/day-17-observability/), [Day 25](/days/day-25-internal-platform/) (cluster, images or secrets created there).
- Uses [`tools/versions.env`](/tools/) (for example from `day-27-durable-workflows-temporal/temporal/.forgejo/workflows/dispatch.yaml`).
- Files from this folder are used by [Day 35](/days/day-35-durable-agents-eve/).

## Homework

Deliverables go in `~/heyjob-labs/day27/` (never commit credentials). Each has a self-check.

### Exercise 1: Run the bad script, kill it, document the loss
**Do:** run `month_end.py`, kill it in step 2 and again in step 4, and write what is lost each time.
### Exercise 2: Kill a worker, prove nothing finished was redone
**Do:** run the workflow with two workers (or two pods), kill the one running `generate_pdfs`, and export the event history.
### Exercise 3: Declarative retries
**Do:** make an activity fail three times (`IRS_FAIL_TIMES=3`) and read the retry policy in the UI.
### Exercise 4: A signal-based approval
**Do:** approve a batch from the CLI. Then **reject** another and read the compensation.
### Exercise 5: Convert one of your own scripts
**Do:** take a script you own (or use the template below). Split it into at least **three activities**, write a workflow with timeouts and a retry policy, and add **time-skipping tests**, including one where an activity fails twice.
### Exercise 6: Wire the dispatch job
**Do:** put `dispatch.yaml` in a repo on your Forgejo, fix the runner label and addresses, and make CI exit green while the workflow keeps running.
### Exercise 7: A Schedule
**Do:** create a Temporal Schedule for the monthly kickoff, trigger it manually, then pause it (`temporal schedule toggle --pause --reason ...`) and delete it.
### Exercise 8: Smell test, three scenarios
**Do:** for each, say "Temporal", "CI", "Job" or "CronJob", and why: (a) a nightly cache warm-up that is safe to run twice; (b) onboarding that emails on day 0, 3 and 7 and waits for a profile to be completed; (c) a 25-minute integration test suite.
### Exercise 9: The detour
**Do:** record `docker stats` memory before and after stopping a cluster you are not using. Optionally build the two-cluster lab and reach the shared service from `app-foo`.
### Exercise 10: Break it
**Do:** (a) put `datetime.now()` in workflow code and read the error; (b) set `start_to_close_timeout` far too low (1 second) on `generate_pdfs` and diagnose it **from the UI**.
