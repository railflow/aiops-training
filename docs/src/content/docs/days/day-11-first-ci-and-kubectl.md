---
title: "Day 11: Your first CI pipeline, and how kubectl really works"
description: "Files in day-11-first-ci-and-kubectl/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 11: Your first CI pipeline, and how kubectl really works"
  order: 11
---

This page is the file-by-file guide to [`day-11-first-ci-and-kubectl/`](https://github.com/railflow/aiops-training/tree/main/day-11-first-ci-and-kubectl) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Have Claude Code draft a Forgejo Actions workflow that tests, measures coverage, scans, builds, pushes to Nexus and collects artifacts; deploy the result with kubectl and look inside kubectl.

Homework for this day is in [`day-11-first-ci-and-kubectl/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-11-first-ci-and-kubectl/homework.md) and is repeated at the bottom of this page.

## What is in the folder

2 files. Paths below are relative to the repo root unless noted.

### day-11-first-ci-and-kubectl/ci/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ci/hello-py-ci.yaml` | Deployed by hand with kubectl in Day 11. The image tag is replaced by `kubectl set image`. Defines: Deployment, Service, Ingress. | `kubectl apply -f day-11-first-ci-and-kubectl/ci/hello-py-ci.yaml` |
| `ci/python-ci.yaml` | First CI pipeline for the Python app, in the hello-apps repo (copy to .forgejo/workflows/python-ci.yaml). Everything happens inside the job, so it is slow on purpose: Day 12 and Day 13 fix that. | `cp day-11-first-ci-and-kubectl/ci/python-ci.yaml .forgejo/workflows/python-ci.yaml` |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ~/heyjob-labs/hello-apps
mkdir -p .forgejo/workflows
cp day-11-first-ci-and-kubectl/ci/python-ci.yaml .forgejo/workflows/python-ci.yaml
git add .forgejo && git commit -m "Add Python CI: test, scan, build and push" && git push
```

```bash
cd ~/aiops-training
kubectl apply -f day-11-first-ci-and-kubectl/ci/hello-py-ci.yaml
kubectl -n apps set image deploy/hello-py-ci hello-py=localhost:30500/hello-py-app:$SHA
kubectl -n apps rollout status deploy/hello-py-ci
curl -s http://hello-py-ci.localhost:8080/hello; echo
kubectl -n apps get deploy hello-py-ci -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

```bash
sed 's/replicas: 2/replicas: 3/' day-11-first-ci-and-kubectl/ci/hello-py-ci.yaml > /tmp/hello-py-ci.yaml
kubectl create -f /tmp/hello-py-ci.yaml 2>&1 | head -3
kubectl diff -f /tmp/hello-py-ci.yaml
kubectl apply --dry-run=server -f /tmp/hello-py-ci.yaml
kubectl apply -f /tmp/hello-py-ci.yaml
kubectl -n apps get deploy hello-py-ci -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | jq -r '.spec.replicas'
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
python-ci / build
  ✓ Set up job                              12s
  ✓ Install tools (slow, repeated on every run)   58s
  ✓ Unit tests and coverage                 31s
  ✓ Scan the source tree                    19s
  ✓ Build image                             44s
  ✓ Scan the image                          27s
  ✓ Push image to Nexus                      6s
  ✓ Collect reports                          1s
  ✓ upload-artifact                          2s
```

```text
deployment "hello-py-ci" successfully rolled out
{"message":"Hello, world!","pod":"hello-py-ci-...","served_by":"python"}
localhost:30500/hello-py-app:3f2a9c1d4e...
```

## How these files relate to other days and shared tools

- Builds on [Day 8](/days/day-08-security-and-supply-chain/), [Day 9](/days/day-09-build-tools-and-tests/), [Day 10](/days/day-10-local-platform/) (cluster, images or secrets created there).
- Files from this folder are used by [Day 13](/days/day-13-ci-at-scale-build-sh/).

## Homework

Work in `~/heyjob-labs/day11/`.

### Exercise 1: Review Claude's workflow

**Do:** ask Claude Code for a workflow for the **Go** app (`go-api`), then review it with the checklist. Record, in `review.md`, three things you changed or rejected and why.

### Exercise 2: Timing table

**Do:** run the Python pipeline three times (push an empty commit with `git commit --allow-empty`). Record per-step times in `timing.md`.

### Exercise 3: Go and Java pipelines

**Do:** write `go-ci.yaml` and `java-ci.yaml` (tests, coverage, image build, push). For Java use `mvn -B verify` and archive the surefire and JaCoCo reports.

### Exercise 4: kubectl detective

**Do:** with `-v=8`, find the exact URL and HTTP method kubectl uses for `kubectl -n apps delete pod <name>` and for `kubectl -n apps scale deploy hello-py-ci --replicas=1`. Put both in `kubectl-internals.md`.

### Exercise 5: Make it fail safely

**Do:** add `--exit-code 1 --severity CRITICAL` to the image scan, push the **vulnerable** image from Day 8 as a test, confirm the pipeline stops before the push step, then revert.
