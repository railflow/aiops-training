---
title: "Day 24: Container patching and hardening"
description: "Files in day-24-container-patching/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 24: Container patching and hardening"
  order: 24
---

This page is the file-by-file guide to [`day-24-container-patching/`](https://github.com/railflow/aiops-training/tree/main/day-24-container-patching) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Choose and pin base images, keep them fresh with digest bumps, debug images that have no shell, and shrink what an attacker gets with security contexts, Pod Security and policy.

Homework for this day is in [`day-24-container-patching/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-24-container-patching/homework.md) and is repeated at the bottom of this page.

## What is in the folder

This day has no sample files of its own. The folder holds the homework and a README only. The lesson uses files from other folders, listed below.

## Files this day uses from other folders

From [Day 3](/days/day-03-kind-kubernetes/): `day-03-kind-kubernetes/` (`k8s/`).

#### day-03-kind-kubernetes/k8s/

| File | What it is | How the lesson uses it |
|---|---|---|
| `hello-go.yaml` | Kubernetes manifest defining Deployment `hello-go`. |  |
| `hello-java.yaml` | Kubernetes manifest defining Deployment `hello-java`. |  |
| `hello-python-oneshot.yaml` | Deliberate mistake for the lab: hello.py exits after one line, so a Deployment (which wants a process that never ends) restarts it forever: CrashLoopBackOff. Defines: Deployment `hello-oneshot`. |  |
| `hello-python.yaml` | Kubernetes manifest defining Deployment `hello-py`. |  |
| `kind-config-calico.yaml` | Same as kind-config.yaml, but without kind's default CNI (kindnet does NOT enforce NetworkPolicy) so that Calico can be installed. |  |
| `kind-config.yaml` | Cluster config for the course. Create it with the kind CLI (see day03): sed "s\|__SHARED_DIR__\|$HOME/kind-shared\|" day-03-kind-kubernetes/k8s/kind-config.yaml &gt; /tmp/kind-config.yaml kind create cluster --config /tmp/kind-config.yaml Defines: Cluster. |  |
| `pvc-demo.yaml` | A PersistentVolumeClaim asks the cluster for storage. kind ships a default StorageClass ("standard", rancher local-path) that creates the volume on demand. Defines: PersistentVolumeClaim `demo-data`, Pod `pvc-writer`. |  |
| `shared-emptydir.yaml` | Two containers in ONE pod share an emptyDir volume. The pod's volume lives exactly as long as the pod. Defines: Pod `shared-emptydir`. |  |
| `shared-hostpath.yaml` | /shared inside the kind node is the folder you mounted via extraMounts in kind-config.yaml, which is a folder on your own machine. Defines: Pod `shared-hostpath`. |  |

From [Day 23](/days/day-23-server-and-application-patching/): `day-23-server-and-application-patching/` (`patching/`).

#### day-23-server-and-application-patching/patching/

| File | What it is | How the lesson uses it |
|---|---|---|
| `dependabot.yml` | GitHub-hosted repositories only: goes to .github/dependabot.yml. On Forgejo use Renovate (renovate.json). |  |
| `renovate.json` | JSON data or configuration file. |  |
| `app/.dockerignore` | Files kept out of the Docker build context. |  |
| `app/Dockerfile` | Pinned by tag AND digest. The digest was read from Docker Hub on 2026-11-05 and WILL be out of date: read the current one yourself (see Day 24) and let Renovate keep it fresh. |  |
| `app/app.py` | Tiny service whose only job is to say exactly which dependency versions it runs. |  |
| `app/requirements.fixed.txt` | Pinned Python dependencies for this folder. |  |
| `app/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `app/tests/test_app.py` | Automated tests for app. |  |
| `ci/patch-gate.sh` | Scan source and image, write an SBOM, and fail when a fixable HIGH/CRITICAL finding exists. |  |
| `containers/Dockerfile.alpine` | Alpine uses musl libc instead of glibc. Small, but some Python wheels and native libraries behave differently: test your real app before choosing it. |  |
| `containers/Dockerfile.full` | Build context: ../app docker build -f ../containers/Dockerfile.full -t patch-demo:full . The convenient default: a full Debian-based image with compilers and many packages you do not need. |  |
| `containers/Dockerfile.slim` | Same app on the "slim" variant: fewer packages, same Debian family. Runs as root unless you say otherwise. |  |
| `containers/Dockerfile.slim-hardened` | Slim, pinned by tag AND digest (digest read 2026-11-05: refresh it, see the lesson), non-root, dependencies installed in a build stage so pip and its caches do not ship in the final image. |  |
| `containers/compare-bases.sh` | Build the demo app on several bases and print size and HIGH/CRITICAL counts side by side. ./containers/compare-bases.sh Requires docker. Trivy runs as the course's pinned container. Counts change daily: capture your own. |  |
| `containers/go-distroless/Dockerfile` | Build context: ../../../../day-07-traefik-ingress/go-api (the Go API from Day 7) A static Go binary needs no OS userland at all. |  |
| `gitops/patch-demo/canary.yaml` | Kubernetes manifest defining Canary. |  |
| `gitops/patch-demo/deployment.yaml` | Kubernetes manifest defining Deployment. |  |
| `gitops/patch-demo/ingressroute.yaml` | Kubernetes manifest defining IngressRoute. |  |
| `gitops/patch-demo/kustomization.yaml` | Copy this folder to apps/patch-demo/ in the hello-config repo and add a Flux Kustomization for it (or extend the existing `apps` one). It shares the namespace and load tester that Day 22 created. Defines: Kustomization. |  |
| `k8s/bluegreen.yaml` | Blue/green by hand: two full Deployments, one Service whose selector decides who gets traffic. Switch with: kubectl -n patch-demo patch svc patch-demo-bg -p '&#123;"spec":&#123;"selector":&#123;"app":"patch-demo-bg","color":"green"&#125;&#125;&#125;' Defines: Deployment, Deployment, Service. |  |
| `k8s/patch-demo.yaml` | Kubernetes manifest defining Namespace, Deployment, Service. |  |
| `k8s/pdb.yaml` | Lets a node drain proceed while keeping at least one pod of the app serving. Defines: PodDisruptionBudget. |  |
| `k8s/restricted/deploy-restricted.yaml` | The "after": non-root, no privilege escalation, no capabilities, read-only root filesystem, a seccomp profile, no service account token it does not need, and resource limits. Passes the restricted profile. Defines: Deployment. |  |
| `k8s/restricted/deploy-root.yaml` | The "before": defaults everywhere. Under the restricted profile this pod is REJECTED (see the Deployment's events). Defines: Deployment. |  |
| `k8s/restricted/namespace.yaml` | Pod Security Admission: enforce the "restricted" profile for every pod created in this namespace. warn and audit labels make the API server say so before you hit enforce: useful when rolling the policy out. Defines: Namespace `hardened`. |  |
| `k8s/restricted/networkpolicy.yaml` | Default deny for everything in the namespace, then one explicit allow: traffic from the Traefik namespace to the app. ENFORCEMENT NEEDS A CNI THAT IMPLEMENTS NetworkPolicy. kind's default (kindnet) may not: use the Calico setup from Day 6 Defines: NetworkPolicy, NetworkPolicy. |  |
| `policies/no-latest.rego` | OPA policy written in Rego. |  |
| `policies/no-latest_test.rego` | Automated tests for no latest. |  |
| `runbooks/emergency-patch.md` | Document: Runbook: emergency patch for a vulnerable dependency or base image |  |
| `sbom/sbom_query.py` | Package names differ in case and separators between tools (Jinja2 vs jinja2, python_dateutil vs python-dateutil). |  |
| `sbom/test_sbom_query.py` | Automated tests for sbom query. |  |
| `sbom/samples/billing.cdx.json` | JSON data or configuration file. |  |
| `sbom/samples/legacy-batch.cdx.json` | JSON data or configuration file. |  |
| `sbom/samples/orders-api.cdx.json` | JSON data or configuration file. |  |
| `sbom/samples/web.cdx.json` | JSON data or configuration file. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

This day has no commands that run files from this repository; it is explained in the lesson. See the homework below for what to run.

## Expected output

Each command should finish without an error. If one exits non-zero, check the earlier commands first and compare with the lesson on the course site.

## How these files relate to other days and shared tools

- Builds on [Day 6](/days/day-06-networking-and-network-policy/), [Day 15](/days/day-15-guard-rails-and-opa/), [Day 23](/days/day-23-server-and-application-patching/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 3](/days/day-03-kind-kubernetes/).
- The lesson also uses files from [Day 23](/days/day-23-server-and-application-patching/).

## Homework

### Exercise 1: Choose a base for your own app

**Do:** pick an app from earlier days, evaluate two bases, and write a one-page decision with size, findings (dated), debug story and risks.
### Exercise 2: Multi-stage everything

**Do:** convert one `Dockerfile` so build tools and caches stay in a builder stage.
### Exercise 3: Break it, a root image under restricted

**Do:** deploy an image that insists on running as root (for example the stock `nginx` image, which expects to bind port 80 as root) into `hardened`.
### Exercise 4: DNS for the default-deny namespace

**Do:** extend the NetworkPolicy so pods in `hardened` can resolve names (egress to kube-dns on port 53) and nothing else.
### Exercise 5: Extend the policy

**Do:** add rules to `no-latest.rego` that deny `hostNetwork: true` and containers with no `resources.limits.memory`, each with a test.
### Exercise 6: A scheduled rebuild

**Do:** write the workflow that rebuilds, scans, and fails loudly when the weekly scan finds something new.
### Exercise 7: Read a vendor's terms

**Do:** pick one hardened-image vendor and one Bitnami-style catalogue, and write down what is free, what is paid, which tags you can pin, and how updates are delivered. Cite the page and date.
