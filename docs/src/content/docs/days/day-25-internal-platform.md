---
title: "Day 25: Building an internal platform for hosting apps and APIs"
description: "Files in day-25-internal-platform/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 25: Building an internal platform for hosting apps and APIs"
  order: 25
---

This page is the file-by-file guide to [`day-25-internal-platform/`](https://github.com/railflow/aiops-training/tree/main/day-25-internal-platform) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Replace ticket-driven infrastructure with a paved road - a golden-path template, shared data services, and Appwrite as a self-hosted backend - and consolidate duplicated databases.

Homework for this day is in [`day-25-internal-platform/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-25-internal-platform/homework.md) and is repeated at the bottom of this page.

## What is in the folder

This day has no sample files of its own. The folder holds the homework and a README only. The lesson uses files from other folders, listed below.

## Files this day uses from other folders

From [Day 10](/days/day-10-local-platform/): `day-10-local-platform/` (`platform/`).

#### day-10-local-platform/platform/

| File | What it is | How the lesson uses it |
|---|---|---|
| `00-namespace.yaml` | Kubernetes manifest defining Namespace `platform`. |  |
| `forgejo.yaml` | Forgejo (Git + issues + Actions) with SQLite, for learning only. The ROOT_URL is the in-cluster address so Actions job containers can clone from it. Defines: PersistentVolumeClaim, Deployment, Service, Ingress. |  |
| `inventory.sh` | The Infra detour, step 1: what data services does this cluster actually run, and who runs how many of them? Read-only. Needs kubectl and jq. |  |
| `nexus-repos.sh` | Create three hosted repositories in Nexus through its REST API: |  |
| `nexus.yaml` | Sonatype Nexus Repository Community Edition: one registry for images, Maven artifacts and Python packages. Needs roughly 2 to 3 GB of memory. Pin the image tag you actually use in tools/versions.env. Defines: PersistentVolumeClaim, Deployment, Service. |  |
| `platform` | The platform's front door: one command for the common chores. ./platform --help Run it from Git Bash or WSL on Windows. It needs: bash, sed, and (for db/bucket/inventory) kubectl. |  |
| `runner.yaml` | Forgejo Runner with a Docker-in-Docker sidecar (privileged; learning only). |  |
| `app-template/.dockerignore` | Files kept out of the Docker build context. |  |
| `app-template/.gitignore` | Files git should not track for this folder. |  |
| `app-template/Dockerfile` | Digest pinning and a bot to keep it fresh: see Day 24. Read the digest yourself with `docker buildx imagetools inspect`. |  |
| `app-template/README.md` | Document: __APP__ |  |
| `app-template/app.py` | Starter service. Replace the / route with your own; keep /healthz, /readyz and /version. |  |
| `app-template/gatus-endpoint.yaml` | Add under `endpoints:` in the Gatus config (day-21-is-my-app-up-gatus/gatus/config/config.yaml), group "apps". |  |
| `app-template/renovate.json` | JSON data or configuration file. |  |
| `app-template/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `app-template/.forgejo/workflows/ci.yaml` | YAML configuration. |  |
| `app-template/docs/api.md` | Document: __APP__ API |  |
| `app-template/docs/architecture.md` | Document: __APP__ architecture |  |
| `app-template/docs/runbook.md` | Document: Runbook: __APP__ |  |
| `app-template/docs/adr/0000-template.md` | Document: NNNN. Title in the form of a decision |  |
| `app-template/docs/adr/0001-record-architecture-decisions.md` | Document: 0001. Record architecture decisions |  |
| `app-template/k8s/deployment.yaml` | Kubernetes manifest defining Deployment. |  |
| `app-template/k8s/ingressroute.yaml` | Kubernetes manifest defining IngressRoute. |  |
| `app-template/k8s/namespace.yaml` | Kubernetes manifest defining Namespace `__APP__`. |  |
| `app-template/k8s/networkpolicy.yaml` | Default deny, then allow: Traefik in, DNS out, and (when the platform provisioned them) Postgres out. Enforced only by a CNI that implements NetworkPolicy (Calico in Day 6). Review before you rely on it. Defines: NetworkPolicy, NetworkPolicy, NetworkPolicy. |  |
| `app-template/k8s/service.yaml` | Kubernetes manifest defining Service. |  |
| `app-template/tests/test_app.py` | Automated tests for app. |  |
| `appwrite/values-local.yaml` | Appwrite on the course's kind cluster (Traefik from Day 7, reached at http://appwrite.localhost:8080). |  |
| `appwrite-app/appwrite.config.json` | JSON data or configuration file. |  |
| `appwrite-app/gatus-endpoint.yaml` | Add under `endpoints:` in the Gatus config (group "platform"). Gatus runs in the cluster, so it calls Traefik's Service and sets the Host header; `[BODY].x` needs a JSON response. |  |
| `appwrite-app/setup_tables.py` | Create the guestbook database, table and columns in a local Appwrite. Safe to run twice (409 means "already there"). |  |
| `appwrite-app/test_setup_tables.py` | Automated tests for setup tables. |  |
| `appwrite-app/functions/guestbook/src/main.py` | Guestbook API as an Appwrite Function (python-3.12). |  |
| `appwrite-app/functions/guestbook/src/store.py` | Two interchangeable stores for guestbook entries. |  |
| `appwrite-app/functions/guestbook/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `appwrite-app/functions/guestbook/tests/test_main.py` | Automated tests for main. |  |
| `appwrite-app/k6/smoke.js` | k6 smoke test through Appwrite's execution API. Needs the k6 binary (or the grafana/k6 container) and: |  |
| `appwrite-functions/go-hello/README.md` | Go starter. The `go.sum` file is not included because Go was not available where this was written: generate it with |  |
| `appwrite-functions/go-hello/go.mod` | Go module definition. |  |
| `appwrite-functions/go-hello/main.go` | Appwrite Function (runtime go-1.26). The runtime calls handler.Main once per request. |  |
| `appwrite-functions/net-probe/src/main.py` | Diagnostic function: can code running inside the Appwrite executor reach the places you need? |  |
| `appwrite-functions/net-probe/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `appwrite-functions/net-probe/tests/test_main.py` | Automated tests for main. |  |
| `appwrite-functions/node-hello/main.test.js` | Automated tests for main. |  |
| `appwrite-functions/node-hello/package.json` | Node project manifest for node-hello. Scripts: test. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

This day has no commands that run files from this repository; it is explained in the lesson. See the homework below for what to run.

## Expected output

Each command should finish without an error. If one exits non-zero, check the earlier commands first and compare with the lesson on the course site.

## How these files relate to other days and shared tools

- Builds on [Day 4](/days/day-04-data-services-and-appwrite/), [Day 10](/days/day-10-local-platform/), [Day 16](/days/day-16-secrets-management-openbao/), [Day 21](/days/day-21-is-my-app-up-gatus/), [Day 22](/days/day-22-progressive-delivery-flux-flagger/), [Day 24](/days/day-24-container-patching/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 10](/days/day-10-local-platform/).

## Homework

Work in `~/heyjob-labs/day25/`.

### Exercise 1: Extend the template

**Do:** add a Flagger `Canary` and an `IngressRoute` variant to `app-template/`, and make `platform new` accept `--lang go`.
### Exercise 2: A quota

**Do:** limit each app database's connections (`ALTER ROLE ... CONNECTION LIMIT n`) in `provision-db.sh`, with a comment explaining the number.
### Exercise 3: Row-level isolation proof

**Do:** show that role `alpha` cannot read database `beta` (`psql` error text in your notes) and that `PUBLIC` has no connect privilege.
### Exercise 4: Decide, in writing

**Do:** write a one-page decision for a hypothetical app with strict compliance needs: shared Postgres, dedicated Postgres, or managed service.
### Exercise 5: Break it, a noisy neighbour

**Do:** run a deliberately heavy query in one database (for example a large `generate_series` cross join) and watch another database's latency with a simple `pgbench` or timing loop.
### Exercise 6: Appwrite hardening review

**Do:** read the Appwrite chart's security and production guides and list five settings you would change before real users. Cite the page.
### Exercise 7: Review an AI-built dashboard

**Do:** have an assistant generate the dashboard from step 15, then review it with the checklist and fix at least two problems.
