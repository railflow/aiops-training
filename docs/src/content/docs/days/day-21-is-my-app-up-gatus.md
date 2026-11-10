---
title: "Day 21: Is my app up and OK? Health endpoints, probes and Gatus"
description: "Files in day-21-is-my-app-up-gatus/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 21: Is my app up and OK? Health endpoints, probes and Gatus"
  order: 21
---

This page is the file-by-file guide to [`day-21-is-my-app-up-gatus/`](https://github.com/railflow/aiops-training/tree/main/day-21-is-my-app-up-gatus) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Give every app honest health endpoints, wire Kubernetes probes, add an outside-in status page and checker with Gatus, and send its failures into Keep as one correlated incident.

Homework for this day is in [`day-21-is-my-app-up-gatus/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-21-is-my-app-up-gatus/homework.md) and is repeated at the bottom of this page.

## What is in the folder

4 files. Paths below are relative to the repo root unless noted.

### day-21-is-my-app-up-gatus/gatus/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gatus/apps-v2.yaml` | Day 21: the three REST apps from Day 7 with real health endpoints and the three probe types. | `kubectl apply -f day-21-is-my-app-up-gatus/gatus/apps-v2.yaml` |
| `gatus/gatus.yaml` | Gatus as a plain Deployment + ConfigMap + Service + Ingress. We mount the config DIRECTORY (not a single file) because Gatus reloads the file on change and the README warns that updates may be missed when a single file is bind-mounted. Defines: Namespace, Deployment, Service, Ingress. |  |
| `gatus/kustomization.yaml` | kubectl apply -k day-21-is-my-app-up-gatus/gatus (creates the ConfigMap from config/config.yaml and the Deployment, Service, Ingress) Create the Secret first (see the lesson): gatus-keep with key KEEP_API_KEY. Defines: Kustomization. |  |

### day-21-is-my-app-up-gatus/gatus/config/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gatus/config/config.yaml` | Gatus configuration. Every endpoint is probed from OUTSIDE the apps (blackbox), on an interval. |  |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

From [Day 7](/days/day-07-traefik-ingress/): `day-07-traefik-ingress/` (`go-api/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-02-docker-basics/python-hello
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

```bash
cd ~/aiops-training
docker build -f day-02-docker-basics/python-hello/Dockerfile.app -t hello-py-app:1.2 day-02-docker-basics/python-hello
docker build -t hello-java-app:1.2 day-04-data-services-and-appwrite/java-app
docker build -t hello-go-api:1.1 day-07-traefik-ingress/go-api
kind load docker-image hello-py-app:1.2 hello-java-app:1.2 hello-go-api:1.1 --name ai-ops-training
```

```bash
kubectl apply -f day-21-is-my-app-up-gatus/gatus/apps-v2.yaml
kubectl -n apps rollout status deploy/hello-py deploy/hello-java deploy/hello-go
```

```bash
kubectl apply -k day-21-is-my-app-up-gatus/gatus
kubectl -n gatus rollout status deploy/gatus
```

```bash
kubectl apply -k day-21-is-my-app-up-gatus/gatus
kubectl -n gatus logs deploy/gatus --tail=20
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
.............                                                            [100%]
13 passed in 2.71s
```

```text
namespace/gatus unchanged
configmap/gatus-config created
service/gatus created
deployment.apps/gatus created
ingress.networking.k8s.io/gatus created
deployment "gatus" successfully rolled out
```

## How these files relate to other days and shared tools

- Builds on [Day 7](/days/day-07-traefik-ingress/), [Day 17](/days/day-17-observability/), [Day 20](/days/day-20-alerting-with-keep/) (cluster, images or secrets created there).
- Uses [`tools/versions.env`](/tools/) (for example from `day-21-is-my-app-up-gatus/gatus/gatus.yaml`).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- The lesson also uses files from [Day 4](/days/day-04-data-services-and-appwrite/).
- The lesson also uses files from [Day 7](/days/day-07-traefik-ingress/).
- Files from this folder are used by [Day 10](/days/day-10-local-platform/), [Day 26](/days/day-26-appwrite-hands-on/).

## Homework

Work in `~/heyjob-labs/day21/`.

### Exercise 1: Endpoints and probes in your own app

**Do:** add `/healthz`, `/readyz` and `/version` to one of your own apps (not just the hello apps) and give its Deployment startup, liveness and readiness probes. Write one test for each endpoint, including a failing readiness test.

### Exercise 2: Three Gatus endpoints

**Do:** add three endpoints to `config.yaml` for your app: a health check, a version assertion (`[BODY].version == ...`), and one **business** check with a response-time condition. Use a Service DNS URL for one and the Traefik `Host` header for another.

### Exercise 3: Fail one on purpose

**Do:** make one endpoint fail (wrong version string, or scale the app to zero) and capture the Gatus log lines for failure and recovery.

### Exercise 4: Webhook to Keep

**Do:** verify the Gatus failure arrives in Keep as a firing alert and later resolves.

### Exercise 5: Deduplicate with a ClickHouse alert

**Do:** cause a failure that both a ClickHouse alert and a Gatus alert detect, and show them in a single Keep incident through a correlation rule. Then decide whether the notification should fire per alert or per incident and implement your choice.

### Exercise 6: Tune against flapping

**Do:** make `hello-java` slow on purpose (for example `INJECT`-style delay or a small CPU limit) so its response time hovers around the threshold. Tune `failure-threshold`, `success-threshold`, `interval` and the condition until it neither pages on a blip nor misses a real outage.

### Exercise 7: Break it

**Do:** replace the `gatus-keep` Secret with a **wrong** API key, restart Gatus, make an endpoint fail, and diagnose from Gatus's logs why no alert appeared in Keep.
