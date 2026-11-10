---
title: "Day 10: A local enterprise-like platform (Forgejo and Nexus)"
description: "Files in day-10-local-platform/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 10: A local enterprise-like platform (Forgejo and Nexus)"
  order: 10
---

This page is the file-by-file guide to [`day-10-local-platform/`](https://github.com/railflow/aiops-training/tree/main/day-10-local-platform) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Run a Git server with issues and Actions, and an artifact registry for images, jars, and Python packages, on your kind cluster.

Homework for this day is in [`day-10-local-platform/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-10-local-platform/homework.md) and is repeated at the bottom of this page.

## What is in the folder

63 files. Paths below are relative to the repo root unless noted.

### day-10-local-platform/platform/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/00-namespace.yaml` | Kubernetes manifest defining Namespace `platform`. | `kubectl apply -f day-10-local-platform/platform/00-namespace.yaml` |
| `platform/forgejo.yaml` | Forgejo (Git + issues + Actions) with SQLite, for learning only. The ROOT_URL is the in-cluster address so Actions job containers can clone from it. Defines: PersistentVolumeClaim, Deployment, Service, Ingress. | `cat day-10-local-platform/platform/forgejo.yaml` |
| `platform/inventory.sh` | The Infra detour, step 1: what data services does this cluster actually run, and who runs how many of them? Read-only. Needs kubectl and jq. |  |
| `platform/nexus-repos.sh` | Create three hosted repositories in Nexus through its REST API: | `day-10-local-platform/platform/nexus-repos.sh` |
| `platform/nexus.yaml` | Sonatype Nexus Repository Community Edition: one registry for images, Maven artifacts and Python packages. Needs roughly 2 to 3 GB of memory. Pin the image tag you actually use in tools/versions.env. Defines: PersistentVolumeClaim, Deployment, Service. | `kubectl apply -f day-10-local-platform/platform/nexus.yaml` |
| `platform/platform` | The platform's front door: one command for the common chores. ./platform --help Run it from Git Bash or WSL on Windows. It needs: bash, sed, and (for db/bucket/inventory) kubectl. |  |
| `platform/runner.yaml` | Forgejo Runner with a Docker-in-Docker sidecar (privileged; learning only). | `cat day-10-local-platform/platform/runner.yaml \| head -50` |

### day-10-local-platform/platform/app-template/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/app-template/.dockerignore` | Files kept out of the Docker build context. |  |
| `platform/app-template/.gitignore` | Files git should not track for this folder. |  |
| `platform/app-template/Dockerfile` | Digest pinning and a bot to keep it fresh: see Day 24. Read the digest yourself with `docker buildx imagetools inspect`. |  |
| `platform/app-template/README.md` | Document: __APP__ |  |
| `platform/app-template/app.py` | Starter service. Replace the / route with your own; keep /healthz, /readyz and /version. |  |
| `platform/app-template/gatus-endpoint.yaml` | Add under `endpoints:` in the Gatus config (day-21-is-my-app-up-gatus/gatus/config/config.yaml), group "apps". |  |
| `platform/app-template/renovate.json` | JSON data or configuration file. |  |
| `platform/app-template/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `platform/app-template/.forgejo/workflows/ci.yaml` | YAML configuration. |  |
| `platform/app-template/k8s/deployment.yaml` | Kubernetes manifest defining Deployment. |  |
| `platform/app-template/k8s/ingressroute.yaml` | Kubernetes manifest defining IngressRoute. |  |
| `platform/app-template/k8s/namespace.yaml` | Kubernetes manifest defining Namespace `__APP__`. |  |
| `platform/app-template/k8s/networkpolicy.yaml` | Default deny, then allow: Traefik in, DNS out, and (when the platform provisioned them) Postgres out. Enforced only by a CNI that implements NetworkPolicy (Calico in Day 6). Review before you rely on it. Defines: NetworkPolicy, NetworkPolicy, NetworkPolicy. |  |
| `platform/app-template/k8s/service.yaml` | Kubernetes manifest defining Service. |  |
| `platform/app-template/tests/test_app.py` | Automated tests for app. |  |

### day-10-local-platform/platform/appwrite/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/appwrite/values-local.yaml` | Appwrite on the course's kind cluster (Traefik from Day 7, reached at http://appwrite.localhost:8080). |  |

### day-10-local-platform/platform/appwrite-app/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/appwrite-app/appwrite.config.json` | JSON data or configuration file. |  |
| `platform/appwrite-app/gatus-endpoint.yaml` | Add under `endpoints:` in the Gatus config (group "platform"). Gatus runs in the cluster, so it calls Traefik's Service and sets the Host header; `[BODY].x` needs a JSON response. |  |
| `platform/appwrite-app/setup_tables.py` | Create the guestbook database, table and columns in a local Appwrite. Safe to run twice (409 means "already there"). |  |
| `platform/appwrite-app/test_setup_tables.py` | Automated tests for setup tables. |  |
| `platform/appwrite-app/functions/guestbook/src/main.py` | Guestbook API as an Appwrite Function (python-3.12). |  |
| `platform/appwrite-app/functions/guestbook/src/store.py` | Two interchangeable stores for guestbook entries. |  |
| `platform/appwrite-app/functions/guestbook/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `platform/appwrite-app/functions/guestbook/tests/test_main.py` | Automated tests for main. |  |
| `platform/appwrite-app/k6/smoke.js` | k6 smoke test through Appwrite's execution API. Needs the k6 binary (or the grafana/k6 container) and: |  |

### day-10-local-platform/platform/appwrite-functions/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/appwrite-functions/go-hello/README.md` | Go starter. The `go.sum` file is not included because Go was not available where this was written: generate it with |  |
| `platform/appwrite-functions/go-hello/go.mod` | Go module definition. |  |
| `platform/appwrite-functions/go-hello/main.go` | Appwrite Function (runtime go-1.26). The runtime calls handler.Main once per request. |  |
| `platform/appwrite-functions/net-probe/src/main.py` | Diagnostic function: can code running inside the Appwrite executor reach the places you need? |  |
| `platform/appwrite-functions/net-probe/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `platform/appwrite-functions/net-probe/tests/test_main.py` | Automated tests for main. |  |
| `platform/appwrite-functions/node-hello/main.test.js` | Automated tests for main. |  |
| `platform/appwrite-functions/node-hello/package.json` | Node project manifest for node-hello. Scripts: test. |  |
| `platform/appwrite-functions/node-hello/src/main.js` | Appwrite Function (runtime node-22). Entrypoint: src/main.js. The executor calls the default export once per request. |  |
| `platform/appwrite-functions/python-hello/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `platform/appwrite-functions/python-hello/src/main.py` | Appwrite Function (runtime python-3.12). Entrypoint: src/main.py. The runtime calls main(context) once per request. |  |
| `platform/appwrite-functions/python-hello/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `platform/appwrite-functions/python-hello/tests/test_main.py` | Automated tests for main. |  |
| `platform/appwrite-functions/write-row/src/main.py` | Appwrite Function: store a greeting as a row in a TablesDB table, using the function's own ephemeral API key. |  |
| `platform/appwrite-functions/write-row/tests/fakectx.py` | A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets. |  |
| `platform/appwrite-functions/write-row/tests/test_main.py` | Automated tests for main. |  |

### day-10-local-platform/platform/consolidation/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/consolidation/README.md` | Document: Consolidation exercise (Day 25) |  |
| `platform/consolidation/before.sh` | Create (or delete) the "before" scenario: three teams, each with a private Postgres. ./before.sh apply ./before.sh delete |  |
| `platform/consolidation/team-postgres.yaml.tpl` | One team's private Postgres: the "before" picture. Three of these is the problem; thirty is the incident. |  |

### day-10-local-platform/platform/shared-services/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/shared-services/00-namespace.yaml` | Kubernetes manifest defining Namespace `platform-data`. |  |
| `platform/shared-services/kustomization.yaml` | Kubernetes manifest defining Kustomization. |  |
| `platform/shared-services/nats.yaml` | Shared NATS with JetStream (messaging and streams). One account for the lab; real multi-tenancy uses NATS accounts. Defines: StatefulSet, Service. |  |
| `platform/shared-services/networkpolicy.yaml` | Only namespaces labelled platform/uses-data=true may reach the shared services. `platform new` adds the label. Needs a CNI that enforces NetworkPolicy (Calico, Day 6). On kindnet this is documentation, not protection. Defines: NetworkPolicy. |  |
| `platform/shared-services/postgres.yaml` | ONE Postgres for many small apps. Each app gets its own database and role (bin/provision-db.sh). |  |
| `platform/shared-services/seaweedfs.yaml` | Shared S3-compatible object storage. MinIO's community repository is archived (checked 2026-11-05), so this uses SeaweedFS, the store the Appwrite Helm chart also ships. |  |
| `platform/shared-services/bin/create-secrets.sh` | Create the admin Secrets for the shared services. Values are generated here and never printed or committed. ./bin/create-secrets.sh |  |
| `platform/shared-services/bin/provision-bucket.sh` | Give an app its own bucket and S3 credentials in the shared SeaweedFS. |  |
| `platform/shared-services/bin/provision-db.sh` | Give an app its own database and role in the shared Postgres, and hand it the connection details as a Secret. |  |

### day-10-local-platform/platform/workflows/

| File | What it is | How the lesson uses it |
|---|---|---|
| `platform/workflows/hello.yaml` | YAML configuration. | `cp day-10-local-platform/platform/workflows/hello.yaml .forgejo/workflows/hello.yaml` |

### day-10-local-platform/pypkg/

| File | What it is | How the lesson uses it |
|---|---|---|
| `pypkg/pyproject.toml` | Support file. |  |

### day-10-local-platform/pypkg/src/

| File | What it is | How the lesson uses it |
|---|---|---|
| `pypkg/src/hello_greeter/__init__.py` | Python module. Defines: `make_greeting`. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
docker info --format 'Memory: {{.MemTotal}} bytes, CPUs: {{.NCPU}}'
kubectl apply -f day-10-local-platform/platform/00-namespace.yaml
```

```bash
cat day-10-local-platform/platform/forgejo.yaml
kubectl apply -f day-10-local-platform/platform/forgejo.yaml
kubectl -n platform rollout status deploy/forgejo --timeout=300s
kubectl -n platform get pods,svc,pvc,ingress
```

```bash
RUNNER_TOKEN=$(kubectl -n platform exec deploy/forgejo -- forgejo forgejo-cli actions generate-runner-token)
kubectl -n platform create secret generic runner-token --from-literal=token="$RUNNER_TOKEN"
cat day-10-local-platform/platform/runner.yaml | head -50
kubectl apply -f day-10-local-platform/platform/runner.yaml
kubectl -n platform rollout status deploy/forgejo-runner --timeout=300s
kubectl -n platform logs deploy/forgejo-runner -c runner --tail=15
```

```bash
cd ~/heyjob-labs/hello-apps
mkdir -p .forgejo/workflows
cp day-10-local-platform/platform/workflows/hello.yaml .forgejo/workflows/hello.yaml
git add .forgejo && git commit -m "Add a hello workflow" && git push
```

```bash
kubectl apply -f day-10-local-platform/platform/nexus.yaml
kubectl -n platform rollout status deploy/nexus --timeout=600s
kubectl -n platform get pods,svc -l app=nexus
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
Memory: 10446471168 bytes, CPUs: 4
namespace/platform created
```

```text
deployment "forgejo" successfully rolled out
pod/forgejo-xxxxxxxxxx-xxxxx   1/1   Running   0   60s
service/forgejo   ClusterIP   10.96.x.y   <none>   3000/TCP
persistentvolumeclaim/forgejo-data   Bound   ...   2Gi
ingress.networking.k8s.io/forgejo   traefik   forgejo.localhost   80
```

## How these files relate to other days and shared tools

- Builds on [Day 7](/days/day-07-traefik-ingress/), [Day 9](/days/day-09-build-tools-and-tests/) (cluster, images or secrets created there).
- Uses [`tools/versions.env`](/tools/) (for example from `day-10-local-platform/platform/appwrite/values-local.yaml`).
- Refers to files in [Day 21](/days/day-21-is-my-app-up-gatus/) (for example from `day-10-local-platform/platform/app-template/gatus-endpoint.yaml`).
- Refers to files in [Day 33](/days/day-33-message-queues-in-devex/) (for example from `day-10-local-platform/platform/platform`).
- Files from this folder are used by [Day 25](/days/day-25-internal-platform/), [Day 26](/days/day-26-appwrite-hands-on/), [Day 28](/days/day-28-write-good-docs/), [Day 33](/days/day-33-message-queues-in-devex/).

## Homework

Work in `~/heyjob-labs/day10/`.

### Exercise 1: Diagram it

**Do:** draw (mermaid in a `platform.md`) the platform you built, including the two names for Nexus. Add one sentence per box on its corporate equivalent.

### Exercise 2: Issue to commit

**Do:** open an issue in Forgejo ("Add /healthz test"), make a branch, commit a change that references it (`Fixes #2` in the message), push, and open a pull request in the UI.

### Exercise 3: Break the runner

**Do:** scale the runner to zero (`kubectl -n platform scale deploy/forgejo-runner --replicas=0`), push a commit, and observe the run waits; scale it back and watch it pick the job up. Explain what a queue of waiting jobs looks like at 1000 repos.

### Exercise 4: Everything in Nexus

**Do:** list the image, jar, and wheel you published using the Nexus REST API (`/service/rest/v1/components`) and record the three listings.

### Exercise 5: Backups

**Do:** find where Forgejo and Nexus keep their data (`kubectl -n platform get pvc`) and write down what you would back up in a real company, and how often.
