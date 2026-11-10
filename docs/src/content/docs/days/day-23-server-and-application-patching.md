---
title: "Day 23: Server and application patching"
description: "Files in day-23-server-and-application-patching/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 23: Server and application patching"
  order: 23
---

This page is the file-by-file guide to [`day-23-server-and-application-patching/`](https://github.com/railflow/aiops-training/tree/main/day-23-server-and-application-patching) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Patch a vulnerable dependency the immutable way - find it, fix the source, rebuild, scan, sign and roll it out as a canary - and patch a node without downtime.

Homework for this day is in [`day-23-server-and-application-patching/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-23-server-and-application-patching/homework.md) and is repeated at the bottom of this page.

## What is in the folder

35 files. Paths below are relative to the repo root unless noted.

### day-23-server-and-application-patching/patching/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/dependabot.yml` | GitHub-hosted repositories only: goes to .github/dependabot.yml. On Forgejo use Renovate (renovate.json). |  |
| `patching/renovate.json` | JSON data or configuration file. |  |

### day-23-server-and-application-patching/patching/app/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/app/.dockerignore` | Files kept out of the Docker build context. |  |
| `patching/app/Dockerfile` | Pinned by tag AND digest. The digest was read from Docker Hub on 2026-11-05 and WILL be out of date: read the current one yourself (see Day 24) and let Renovate keep it fresh. |  |
| `patching/app/app.py` | Tiny service whose only job is to say exactly which dependency versions it runs. |  |
| `patching/app/requirements.fixed.txt` | Pinned Python dependencies for this folder. | `diff requirements.txt requirements.fixed.txt` |
| `patching/app/requirements.txt` | Pinned Python dependencies for this folder. | `Get-Content requirements.txt` |
| `patching/app/tests/test_app.py` | Automated tests for app. |  |

### day-23-server-and-application-patching/patching/ci/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/ci/patch-gate.sh` | Scan source and image, write an SBOM, and fail when a fixable HIGH/CRITICAL finding exists. |  |

### day-23-server-and-application-patching/patching/containers/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/containers/Dockerfile.alpine` | Alpine uses musl libc instead of glibc. Small, but some Python wheels and native libraries behave differently: test your real app before choosing it. |  |
| `patching/containers/Dockerfile.full` | Build context: ../app docker build -f ../containers/Dockerfile.full -t patch-demo:full . The convenient default: a full Debian-based image with compilers and many packages you do not need. |  |
| `patching/containers/Dockerfile.slim` | Same app on the "slim" variant: fewer packages, same Debian family. Runs as root unless you say otherwise. |  |
| `patching/containers/Dockerfile.slim-hardened` | Slim, pinned by tag AND digest (digest read 2026-11-05: refresh it, see the lesson), non-root, dependencies installed in a build stage so pip and its caches do not ship in the final image. |  |
| `patching/containers/compare-bases.sh` | Build the demo app on several bases and print size and HIGH/CRITICAL counts side by side. ./containers/compare-bases.sh Requires docker. Trivy runs as the course's pinned container. Counts change daily: capture your own. |  |
| `patching/containers/go-distroless/Dockerfile` | Build context: ../../../../day-07-traefik-ingress/go-api (the Go API from Day 7) A static Go binary needs no OS userland at all. |  |

### day-23-server-and-application-patching/patching/gitops/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/gitops/patch-demo/canary.yaml` | Kubernetes manifest defining Canary. |  |
| `patching/gitops/patch-demo/deployment.yaml` | Kubernetes manifest defining Deployment. |  |
| `patching/gitops/patch-demo/ingressroute.yaml` | Kubernetes manifest defining IngressRoute. |  |
| `patching/gitops/patch-demo/kustomization.yaml` | Copy this folder to apps/patch-demo/ in the hello-config repo and add a Flux Kustomization for it (or extend the existing `apps` one). It shares the namespace and load tester that Day 22 created. Defines: Kustomization. |  |

### day-23-server-and-application-patching/patching/k8s/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/k8s/bluegreen.yaml` | Blue/green by hand: two full Deployments, one Service whose selector decides who gets traffic. Switch with: kubectl -n patch-demo patch svc patch-demo-bg -p '&#123;"spec":&#123;"selector":&#123;"app":"patch-demo-bg","color":"green"&#125;&#125;&#125;' Defines: Deployment, Deployment, Service. |  |
| `patching/k8s/patch-demo.yaml` | Kubernetes manifest defining Namespace, Deployment, Service. |  |
| `patching/k8s/pdb.yaml` | Lets a node drain proceed while keeping at least one pod of the app serving. Defines: PodDisruptionBudget. |  |
| `patching/k8s/restricted/deploy-restricted.yaml` | The "after": non-root, no privilege escalation, no capabilities, read-only root filesystem, a seccomp profile, no service account token it does not need, and resource limits. Passes the restricted profile. Defines: Deployment. |  |
| `patching/k8s/restricted/deploy-root.yaml` | The "before": defaults everywhere. Under the restricted profile this pod is REJECTED (see the Deployment's events). Defines: Deployment. |  |
| `patching/k8s/restricted/namespace.yaml` | Pod Security Admission: enforce the "restricted" profile for every pod created in this namespace. warn and audit labels make the API server say so before you hit enforce: useful when rolling the policy out. Defines: Namespace `hardened`. |  |
| `patching/k8s/restricted/networkpolicy.yaml` | Default deny for everything in the namespace, then one explicit allow: traffic from the Traefik namespace to the app. ENFORCEMENT NEEDS A CNI THAT IMPLEMENTS NetworkPolicy. kind's default (kindnet) may not: use the Calico setup from Day 6 Defines: NetworkPolicy, NetworkPolicy. |  |

### day-23-server-and-application-patching/patching/policies/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/policies/no-latest.rego` | OPA policy written in Rego. |  |
| `patching/policies/no-latest_test.rego` | Automated tests for no latest. |  |

### day-23-server-and-application-patching/patching/runbooks/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/runbooks/emergency-patch.md` | Document: Runbook: emergency patch for a vulnerable dependency or base image |  |

### day-23-server-and-application-patching/patching/sbom/

| File | What it is | How the lesson uses it |
|---|---|---|
| `patching/sbom/sbom_query.py` | Package names differ in case and separators between tools (Jinja2 vs jinja2, python_dateutil vs python-dateutil). |  |
| `patching/sbom/test_sbom_query.py` | Automated tests for sbom query. |  |
| `patching/sbom/samples/billing.cdx.json` | JSON data or configuration file. |  |
| `patching/sbom/samples/legacy-batch.cdx.json` | JSON data or configuration file. |  |
| `patching/sbom/samples/orders-api.cdx.json` | JSON data or configuration file. |  |
| `patching/sbom/samples/web.cdx.json` | JSON data or configuration file. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ..    # day-23-server-and-application-patching/patching
trivy fs --scanners vuln --severity HIGH,CRITICAL app
trivy fs --scanners vuln --severity MEDIUM,HIGH,CRITICAL app | head -n 40
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
app/requirements.txt (pip)
Total: N (MEDIUM: ..., HIGH: ...)
┌───────────┬────────────────┬──────────┬────────┬───────────────────┬───────────────┐
│  Library  │ Vulnerability  │ Severity │ Status │ Installed Version │ Fixed Version │
```

## How these files relate to other days and shared tools

- Builds on [Day 8](/days/day-08-security-and-supply-chain/), [Day 10](/days/day-10-local-platform/), [Day 12](/days/day-12-understanding-dependencies/), [Day 22](/days/day-22-progressive-delivery-flux-flagger/) (cluster, images or secrets created there).
- Uses [`tools/versions.env`](/tools/) (for example from `day-23-server-and-application-patching/patching/ci/patch-gate.sh`).
- Refers to files in [Day 3](/days/day-03-kind-kubernetes/) (for example from `day-23-server-and-application-patching/patching/k8s/restricted/networkpolicy.yaml`).
- Refers to files in [Day 7](/days/day-07-traefik-ingress/) (for example from `day-23-server-and-application-patching/patching/containers/go-distroless/Dockerfile`).
- Files from this folder are used by [Day 24](/days/day-24-container-patching/).

## Homework

Work in `~/heyjob-labs/day23/`.

### Exercise 1: Different scanners, different answers

**Do:** scan `patch-demo:1.0.0` with Trivy and with a second scanner (Grype, Docker Scout, or your IDE's), and list the differences.
### Exercise 2: An SBOM store

**Do:** write a script that, for every image your cluster runs, finds or generates its SBOM into one folder named by digest.
### Exercise 3: Renovate rules

**Do:** edit `renovate.json` so that patch updates of a dev-only tool automerge after CI passes, but runtime dependencies never do. Check the option names in the Renovate docs.
### Exercise 4: Break it with `:latest`

**Do:** change the deployment to `image: ...patch-demo:latest`, push an image tagged `latest` with the old pins, deploy, then push a fixed image to the **same** tag and watch what the cluster does (and what a node that already cached the old one does if `imagePullPolicy: IfNotPresent`).
### Exercise 5: A drain that cannot finish

**Do:** set the PodDisruptionBudget to `minAvailable: 3` with 3 replicas, then drain a node.
### Exercise 6: Write the rollback

**Do:** produce a rollback for patch 1.0.1: a `git revert`, and the observed result.
### Exercise 7: Mean time to patch

**Do:** record timestamps for detect, fix commit, merged, canary done, verified in your dry run, and compute the total.
