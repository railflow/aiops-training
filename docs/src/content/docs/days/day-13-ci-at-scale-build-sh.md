---
title: "Day 13: CI at scale with a central build.sh"
description: "Files in day-13-ci-at-scale-build-sh/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 13: CI at scale with a central build.sh"
  order: 13
---

This page is the file-by-file guide to [`day-13-ci-at-scale-build-sh/`](https://github.com/railflow/aiops-training/tree/main/day-13-ci-at-scale-build-sh) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Move logic out of per-repo workflows into one tested script with stack auto-detection, bake a builder image, and build images with BuildKit instead of Docker-in-Docker.

Homework for this day is in [`day-13-ci-at-scale-build-sh/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-13-ci-at-scale-build-sh/homework.md) and is repeated at the bottom of this page.

## What is in the folder

3 files. Paths below are relative to the repo root unless noted.

### day-13-ci-at-scale-build-sh/ci/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ci/buildkit.yaml` | Rootless BuildKit daemon for in-cluster image builds (no Docker socket, no privileged container). Needs Linux user namespaces on the node; kind nodes on Docker Desktop may or may not allow this: if the pod fails, see the troubleshooting table in the lesson. Defines: ConfigMap, Deployment, Service. | `kubectl apply -f day-13-ci-at-scale-build-sh/ci/buildkit.yaml` |
| `ci/central-ci.yaml` | The whole workflow. All logic lives in build.sh and the builder image. Copy to .forgejo/workflows/ci.yaml in each repo (or call it as a reusable workflow). | `wc -l day-11-first-ci-and-kubectl/ci/python-ci.yaml day-13-ci-at-scale-build-sh/ci/central-ci.yaml` |

### day-13-ci-at-scale-build-sh/ci/builder/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ci/builder/Dockerfile` | The "baked" builder image: every tool the central build.sh may call, installed once. Build from the repository root (aiops-training): docker build -f day-13-ci-at-scale-build-sh/ci/builder/Dockerfile -t builder:1 . | `cat day-13-ci-at-scale-build-sh/ci/builder/Dockerfile` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

From [Day 3](/days/day-03-kind-kubernetes/): `day-03-kind-kubernetes/` (`k8s/`).

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

From [Day 7](/days/day-07-traefik-ingress/): `day-07-traefik-ingress/` (`go-api/`).

From [Day 11](/days/day-11-first-ci-and-kubectl/): `day-11-first-ci-and-kubectl/` (`ci/`).

From [Day 12](/days/day-12-understanding-dependencies/): `day-12-understanding-dependencies/` (`deps/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ~/aiops-training
tools/build.sh --help
tools/build.sh --dir day-02-docker-basics/python-hello --dry-run build test
```

```bash
for d in day-04-data-services-and-appwrite/java-app day-07-traefik-ingress/go-api day-12-understanding-dependencies/deps/node-hello; do tools/build.sh --dir $d --dry-run build test | sed -n '1p;4,5p'; done
tools/build.sh --dir day-03-kind-kubernetes/k8s; echo "exit code: $?"
```

```bash
tools/build.sh --dir day-04-data-services-and-appwrite/java-app test
echo "exit code: $?"
ls day-04-data-services-and-appwrite/java-app/reports
```

```bash
cd ~/aiops-training
cat day-13-ci-at-scale-build-sh/ci/builder/Dockerfile
time docker build -f day-13-ci-at-scale-build-sh/ci/builder/Dockerfile -t localhost:30500/builder:1 .
docker images localhost:30500/builder
docker run --rm localhost:30500/builder:1 sh -c "build.sh --help | head -3; trivy --version | head -1; kubectl version --client | head -1; java -version 2>&1 | head -1"
```

```bash
cd ~/aiops-training
kubectl apply -f day-13-ci-at-scale-build-sh/ci/buildkit.yaml
kubectl -n platform rollout status deploy/buildkitd --timeout=180s
kubectl -n platform logs deploy/buildkitd --tail=5
kubectl -n platform exec deploy/buildkitd -- buildctl --addr tcp://127.0.0.1:1234 debug workers
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
build.sh: stack=python steps=build test dir=/.../python-hello image=localhost:30500/python-hello:d3b5617 dry-run=1

==> build (python)
+ python3 -m venv .venv
+ .venv/bin/pip install -q -r requirements-dev.txt
+ docker build -f Dockerfile.app -t localhost:30500/python-hello:d3b5617 .

==> test (python)
+ .venv/bin/pytest --cov=. --cov-report=term --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml

==> done: build test succeeded
```

```text
build.sh: stack=java-maven steps=build test dir=/.../java-app ...
+ mvn -B -DskipTests package
+ docker build -f Dockerfile -t localhost:30500/java-app:d3b5617 .
build.sh: stack=go steps=build test dir=/.../go-api ...
+ go build ./...
...
build.sh: could not detect the stack in /.../k8s (looked for pom.xml, build.gradle, requirements.txt, pyproject.toml, go.mod, package.json)
exit code: 2
```

## How these files relate to other days and shared tools

- Builds on [Day 11](/days/day-11-first-ci-and-kubectl/), [Day 12](/days/day-12-understanding-dependencies/) (cluster, images or secrets created there).
- Uses [`tools/build.sh`](/tools/) (for example from `day-13-ci-at-scale-build-sh/ci/builder/Dockerfile`).
- Uses [`tools/check-docs-touched.sh`](/tools/) (for example from `day-13-ci-at-scale-build-sh/ci/builder/Dockerfile`).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- The lesson also uses files from [Day 3](/days/day-03-kind-kubernetes/).
- The lesson also uses files from [Day 4](/days/day-04-data-services-and-appwrite/).
- The lesson also uses files from [Day 7](/days/day-07-traefik-ingress/).
- The lesson also uses files from [Day 11](/days/day-11-first-ci-and-kubectl/).
- The lesson also uses files from [Day 12](/days/day-12-understanding-dependencies/).
- Files from this folder are used by [Capstone](/days/capstone/), [Day 28](/days/day-28-write-good-docs/).

## Homework

Work in `~/heyjob-labs/day13/`.

### Exercise 1: Run `build.sh` on your three apps

**Do:** run `build.sh build test` for Python, Java, and Go (using Docker only where tools are missing). Save the three transcripts (`python.txt`, `java.txt`, `go.txt`).

### Exercise 2: Add a stack

**Do:** teach `build.sh` about a new stack: detect `Cargo.toml` (Rust) or `composer.json` (PHP) and add build/test commands. Update `usage` text. Keep the other stacks working (run the dry runs again).

### Exercise 3: Exit codes

**Do:** write a tiny test script (`test-build-sh.sh`) that asserts: unknown flag exits 2, undetectable stack exits 2, `--help` exits 0, a dry run exits 0. Run it.

### Exercise 4: Builder image in Nexus

**Do:** build, push, and pull the builder image through Nexus and write down its size and the time of a cold pull versus a cached pull on the runner.

### Exercise 5: DinD versus BuildKit

**Do:** write a half-page comparing DinD and BuildKit for a company with 1,000 repos: security, cache sharing, cost, failure modes, operations.
