---
title: "Day 16: Secrets, part 2: where secrets live (OpenBao), how apps get them, and rotation"
description: "Files in day-16-secrets-management-openbao/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 16: Secrets, part 2: where secrets live (OpenBao), how apps get them, and rotation"
  order: 16
---

This page is the file-by-file guide to [`day-16-secrets-management-openbao/`](https://github.com/railflow/aiops-training/tree/main/day-16-secrets-management-openbao) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Install OpenBao on kind, let the External Secrets Operator sync a secret into Kubernetes, deliver it to a pod as a file, and rotate it without a restart.

Homework for this day is in [`day-16-secrets-management-openbao/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-16-secrets-management-openbao/homework.md) and is repeated at the bottom of this page.

## What is in the folder

6 files. Paths below are relative to the repo root unless noted.

### day-16-secrets-management-openbao/openbao/

| File | What it is | How the lesson uses it |
|---|---|---|
| `openbao/eso-stores.yaml` | External Secrets Operator wiring: how each namespace logs in to OpenBao (Kubernetes auth) and which OpenBao keys become Kubernetes Secrets. | `kubectl apply -f day-16-secrets-management-openbao/openbao/eso-stores.yaml` |
| `openbao/hello-py-env-secret.yaml` | The "break it" variant: the SAME secret delivered as an ENVIRONMENT VARIABLE. Environment variables are fixed when the container starts, so a rotated password is NOT picked up. Defines: Deployment, Service, Ingress. | `kubectl apply -f day-16-secrets-management-openbao/openbao/hello-py-env-secret.yaml` |
| `openbao/hello-py-secrets.yaml` | The Python API reading its database password from a FILE that is a mounted secret. Nothing in this manifest, the image, or the repository contains the password. Defines: Deployment, Service, Ingress. | `kubectl apply -f day-16-secrets-management-openbao/openbao/hello-py-secrets.yaml` |
| `openbao/policy-hello-app.hcl` | Least privilege: read-only access to the hello-app secrets and nothing else. KV version 2 stores data under "data/" and metadata under "metadata/". | `kubectl -n openbao cp day-16-secrets-management-openbao/openbao/policy-hello-app.hcl openbao-0:/tmp/policy-hello-app.hcl` |
| `openbao/rotate-db-password.sh` | Rotate the hello-app database password: change it in Postgres, then in OpenBao. | `bash day-16-secrets-management-openbao/openbao/rotate-db-password.sh` |
| `openbao/values-openbao.yaml` | Helm values for OpenBao in DEV MODE on kind (learning only: in-memory storage, auto-unsealed, a well-known root token, no TLS). Check them against your chart version: helm show values openbao/openbao \| less | `helm upgrade --install openbao openbao/openbao --version 0.30.6 -n openbao --create-namespace -f day-16-secrets-management-openbao/openbao/values-o...` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
helm upgrade --install openbao openbao/openbao --version 0.30.6 -n openbao --create-namespace -f day-16-secrets-management-openbao/openbao/values-openbao.yaml
kubectl -n openbao rollout status statefulset/openbao --timeout=180s
kubectl -n openbao get pods
```

```bash
kubectl -n openbao cp day-16-secrets-management-openbao/openbao/policy-hello-app.hcl openbao-0:/tmp/policy-hello-app.hcl
kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 bao policy write hello-app /tmp/policy-hello-app.hcl
kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 bao auth enable kubernetes
kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 sh -c 'bao write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc:443'
kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 bao write auth/kubernetes/role/hello-app bound_service_account_names=hello-app bound_service_account_namespaces=apps policies=hello-app ttl=1h
kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 bao write auth/kubernetes/role/postgres bound_service_account_names=postgres-eso bound_service_account_namespaces=data policies=hello-app ttl=1h
```

```bash
kubectl create namespace apps --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f day-16-secrets-management-openbao/openbao/eso-stores.yaml
kubectl -n apps get secretstore,externalsecret
kubectl -n apps get secret db-credentials
```

```bash
cd ~/aiops-training
docker build -f day-02-docker-basics/python-hello/Dockerfile.app -t hello-py-app:1.2 day-02-docker-basics/python-hello
kind load docker-image hello-py-app:1.2 --name ai-ops-training
kubectl apply -f day-16-secrets-management-openbao/openbao/hello-py-secrets.yaml
kubectl -n apps rollout status deploy/hello-py-secrets --timeout=120s
```

```powershell
# Run the script in WSL or Git Bash: it uses tr/head and bash
bash day-16-secrets-management-openbao/openbao/rotate-db-password.sh
1..8 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}`n" http://hello-py-secrets.localhost:8080/greetings; Start-Sleep 15 }
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
NAME        READY   STATUS    RESTARTS   AGE
openbao-0   1/1     Running   0          40s
```

```text
Success! Uploaded policy: hello-app
Success! Enabled kubernetes auth method at: kubernetes/
Success! Data written to: auth/kubernetes/config
Success! Data written to: auth/kubernetes/role/hello-app
Success! Data written to: auth/kubernetes/role/postgres
```

## How these files relate to other days and shared tools

- Builds on [Day 4](/days/day-04-data-services-and-appwrite/), [Day 7](/days/day-07-traefik-ingress/), [Day 14](/days/day-14-secrets-detection/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- Files from this folder are used by [Day 19](/days/day-19-observability-dashboards/), [Day 20](/days/day-20-alerting-with-keep/), [Day 29](/days/day-29-ai-tools-foundations/).

## Homework

Work in `~/heyjob-labs/day16/`. Use only generated, throwaway values.

### Exercise 1: Least privilege

**Do:** write a second policy that can read `secret/data/other-team/*` only, and a role that binds it to a ServiceAccount `other` in a namespace `other`. Prove with a SecretStore in `other` that it **cannot** read `hello-app/db`.

### Exercise 2: Rotation timeline

**Do:** run the rotation script while `curl` runs every 2 seconds against both apps. Record when each app's first `200` returns.

### Exercise 3: Shorten the window

**Do:** change `refreshInterval` to `10s`, repeat, and compare. Then write down why you would not set it to `1s` against a real secret store (API load, rate limits, cost).

### Exercise 4: Make the env-var app recover

**Do:** make `hello-py-env` pick up the new password **without** manual commands. Options: add the Reloader controller annotation, or switch it to a file. Pick one and justify it.

### Exercise 5: Dynamic credentials (optional)

**Do:** follow the OpenBao database secrets engine documentation to create a role for Postgres with a 5-minute lease, request credentials twice, and list the users in Postgres (`\du`).
