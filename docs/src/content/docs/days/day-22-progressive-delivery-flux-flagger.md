---
title: "Day 22: Release risk, GitOps with Flux, and progressive delivery with Flagger"
description: "Files in day-22-progressive-delivery-flux-flagger/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 22: Release risk, GitOps with Flux, and progressive delivery with Flagger"
  order: 22
---

This page is the file-by-file guide to [`day-22-progressive-delivery-flux-flagger/`](https://github.com/railflow/aiops-training/tree/main/day-22-progressive-delivery-flux-flagger) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Replace "deploy and hope" with a pull-based GitOps flow and automated canary releases that promote on good metrics and roll back on bad ones.

Homework for this day is in [`day-22-progressive-delivery-flux-flagger/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-22-progressive-delivery-flux-flagger/homework.md) and is repeated at the bottom of this page.

## What is in the folder

12 files. Paths below are relative to the repo root unless noted.

### day-22-progressive-delivery-flux-flagger/gitops/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gitops/traefik-metrics-values.yaml` | Extra values for the Traefik chart so Flagger's Prometheus can scrape Traefik's metrics (Day 22). | `-f day-07-traefik-ingress/traefik/values-kind.yaml -f day-22-progressive-delivery-flux-flagger/gitops/traefik-metrics-values.yaml` |

### day-22-progressive-delivery-flux-flagger/gitops/ch-gate/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gitops/ch-gate/ch-gate.yaml` | Optional extra gate for Flagger (Day 22): asks ClickHouse whether the canary pods are healthy. |  |
| `gitops/ch-gate/gate.py` | A Flagger webhook gate that asks ClickHouse whether the CANARY pods are healthy. |  |
| `gitops/ch-gate/test_gate.py` | Automated tests for gate. | `pytest -q test_gate.py` |

### day-22-progressive-delivery-flux-flagger/gitops/config-repo/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gitops/config-repo/apps/podinfo/canary.yaml` | The release policy as code. Flagger sees the Deployment's pod template change, then: |  |
| `gitops/config-repo/apps/podinfo/deployment.yaml` | The app Flagger will manage. To release a new version, change the image tag in a commit: that is the whole "deploy". Defines: Deployment. | `(Get-Content apps\podinfo\deployment.yaml) -replace 'podinfo:6.7.1','podinfo:6.8.0' \| Set-Content apps\podinfo\deployment.yaml` |
| `gitops/config-repo/apps/podinfo/ingressroute.yaml` | Users reach podinfo through Traefik at http://podinfo.localhost:8080. The "podinfo" TraefikService is created by Flagger: it splits traffic between podinfo-primary and podinfo-canary by weight. Defines: IngressRoute. |  |
| `gitops/config-repo/apps/podinfo/kustomization.yaml` | Kubernetes manifest defining Kustomization. |  |
| `gitops/config-repo/clusters/heyjob-local/README.md` | This repository ("hello-config") is what Flux watches. Layout: |  |
| `gitops/config-repo/infrastructure/flagger.yaml` | Flagger and its load tester, installed by Flux's helm-controller (so even the tools are in git). |  |
| `gitops/config-repo/infrastructure/kustomization.yaml` | Kubernetes manifest defining Kustomization. |  |

### day-22-progressive-delivery-flux-flagger/gitops/flux/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gitops/flux/flux-sync.yaml` | Tells Flux which Git repository to watch and which folder to apply. | `kubectl apply -f day-22-progressive-delivery-flux-flagger/gitops/flux/flux-sync.yaml` |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
mkdir -p ~/heyjob-labs/day22 && cd ~/heyjob-labs/day22
cp -R day-22-progressive-delivery-flux-flagger/gitops/config-repo ./hello-config && cd hello-config
git init -b main
git add -A
git commit -m "Add podinfo with a Flagger canary policy and Flagger via Flux"
curl -s -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
http://forgejo.localhost:8080/api/v1/user/repos -d '{"name":"hello-config","private":false}' | jq -r .full_name
git remote add origin "http://student:$TOKEN@forgejo.localhost:8080/student/hello-config.git"
git push -u origin main
git remote set-url origin http://forgejo.localhost:8080/student/hello-config.git   # remove the token from the URL
```

```bash
kubectl apply -f day-22-progressive-delivery-flux-flagger/gitops/flux/flux-sync.yaml
kubectl -n flux-system get gitrepository,kustomization
```

```bash
helm upgrade traefik traefik/traefik -n traefik \
-f day-07-traefik-ingress/traefik/values-kind.yaml -f day-22-progressive-delivery-flux-flagger/gitops/traefik-metrics-values.yaml
kubectl -n traefik rollout status deploy/traefik
kubectl -n traefik get pod -l app.kubernetes.io/name=traefik -o jsonpath='{.items[0].metadata.annotations}' | jq
```

```bash
cd day-22-progressive-delivery-flux-flagger/gitops/ch-gate
python3 -m pip install pytest   # in a virtual environment
pytest -q test_gate.py
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
student/hello-config
To http://forgejo.localhost:8080/student/hello-config.git
 * [new branch]      main -> main
```

```text
NAME                                    URL                                                        READY   STATUS
gitrepository.source.toolkit.../hello-config   http://forgejo.platform.svc.cluster.local:3000/...   True    stored artifact for revision 'main@sha1:3f2a9c1'
NAME                         READY   STATUS
kustomization.../infrastructure   False   Reconciliation in progress
kustomization.../apps             False   dependency 'flux-system/infrastructure' is not ready
```

## How these files relate to other days and shared tools

- Builds on [Day 7](/days/day-07-traefik-ingress/), [Day 10](/days/day-10-local-platform/), [Day 19](/days/day-19-observability-dashboards/), [Day 20](/days/day-20-alerting-with-keep/) (cluster, images or secrets created there).
- Refers to files in [Day 7](/days/day-07-traefik-ingress/) (for example from `day-22-progressive-delivery-flux-flagger/gitops/traefik-metrics-values.yaml`).

## Homework

Work in `~/heyjob-labs/day22/`.

### Exercise 1: Rolling update math

**Do:** for 4 replicas, write the number of pods that can be unavailable and the maximum total during an update for `maxSurge: 50%, maxUnavailable: 0` and for `maxSurge: 0, maxUnavailable: 1`. Prove one of them with `kubectl get pods -w`.

### Exercise 2: A Flux-synced app

**Do:** add a second app (your own app, or the hello apps with the probes from Day 21) to `hello-config` under `apps/`, with its own Flux Kustomization.

### Exercise 3: A canary that promotes

**Do:** release a new version of your own app through the canary and record the weights in order.

### Exercise 4: A canary that rolls back, on purpose

**Do:** make a failing canary three different ways (HTTP 500s, slowness over the p99 limit, and a failing `pre-rollout` smoke test). 

### Exercise 5: Revert in git

**Do:** after an automatic rollback, use `git revert`, push, and show Flux reconcile to a state that matches the cluster.

### Exercise 6: Tell Keep

**Do:** configure a Flagger `event` webhook (or alert provider) that posts to Keep's `/alerts/event` when a canary fails.

### Exercise 7: Break it

**Do:** make the Flux Secret `forgejo-auth` wrong, push a change, and diagnose why nothing rolls out.
