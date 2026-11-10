---
title: Shared tools
description: "The helpers in tools/: the kind cluster wrapper, build.sh, deploy.sh, versions.env and friends."
sidebar:
  order: 2
---

`tools/` holds the helpers that several days share. Run them from the repo root, for example `./tools/kind start`.

| File | What it is | Used on |
|---|---|---|
| [`tools/kind`](#toolskind) | Bash wrapper around `kind` and `kubectl`: start, stop, destroy, list the course cluster | Day 1 onward |
| [`tools/ports.sh`](#toolsportssh) | Helper that `tools/kind` sources to pick free host ports | via `tools/kind` |
| [`tools/build.sh`](#toolsbuildsh) | One central build script: detects the stack, then builds, tests, scans, measures | Days 13, 14, 15 and the capstone |
| [`tools/deploy.sh`](#toolsdeploysh) | Asks the policy engine (OPA) whether a deploy is allowed, then deploys | Day 15 |
| [`tools/check-docs-touched.sh`](#toolscheck-docs-touchedsh) | CI gate: fails when code changed but docs did not | Day 28 |
| [`tools/coverage_percent.py`](#toolscoverage_percentpy) | Prints the coverage percentage from a Cobertura or JaCoCo XML report | Days 13 and 15 |
| [`tools/versions.env`](#toolsversionsenv) | Pinned image and tool versions the course uses | many days |

## tools/kind

Creates and manages the local kind cluster `ai-ops-training` (kubectl context `kind-ai-ops-training`). It only calls `kind`, `kubectl` and `docker`; it installs nothing. Every command it runs is echoed (lines starting with `▶`).

```bash
./tools/kind start      # checks Docker, kubectl, kind; creates the cluster; deploys a busybox pod
./tools/kind stop       # docker stop on the node containers; the cluster is kept
./tools/kind destroy    # deletes the cluster
./tools/kind list       # kind get clusters
./tools/kind --help     # usage and the underlying commands
```

Useful variables: `KIND_CLUSTER_NAME` (another cluster name), `KIND_HTTP_PORT` and `KIND_HTTPS_PORT` (exact host ports; an error if busy), `KIND_NO_AUTOSTART=1` (do not start Docker for you), `KIND_NO_SUMMARY=1` (hide the closing "Where things are" block), `NO_COLOR=1`, `KIND_NO_EMOJI=1`.

The start of `NO_COLOR=1 ./tools/kind --help` (the file prints more):

```text

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  ☸️  ./tools/kind  —  kind + kubectl made easy  🐳 
┃  Local ai-ops-training cluster  ·  kubectl context kind-ai-ops-training
┃  A thin wrapper. It installs nothing.
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  About
──────────────────────────────────────────────────────────────────
  ./tools/kind is a thin wrapper around the kind and kubectl CLIs.
  It only exposes a few basic functions. kind and kubectl have far more
  capabilities. Use those CLIs directly to learn how they work:

  ▶ kind --help
  ▶ kubectl --help

⚠️  This script will not install anything. Install Docker, kind, and kubectl yourself.

❓ Usage
──────────────────────────────────────────────────────────────────
  ./tools/kind <command>

  🚀 start     start Docker if stopped, create the cluster if needed, start its nodes, run busybox
  🛑 stop      stop the node containers; the cluster is kept
  💥 destroy   delete the cluster
  📋 list      list all kind clusters
  ❓ help      show this usage (also -h, --help, or no args)

✅ Preflight  (each check prints yes or no; the first no stops the command, exit non-zero)
──────────────────────────────────────────────────────────────────
  🐳 check 1  is docker installed and running   (docker info; start may start it, see below)
  ☸️  check 2  is kubectl installed             (command -v kubectl)
  📦 check 3  is kind installed                (command -v kind, then kind version)
  🧪 check 4  test deploy: deploy busybox
     start only, after the cluster is up and busybox is deployed and running.
     Prints the kubectl command used.

     start     runs checks 1, 2, 3, then 4
     stop      runs check 1 (docker) and check 3 (kind); never starts Docker
     destroy   runs check 1 (docker) and check 3 (kind); never starts Docker
     list      runs check 1 (docker) and check 3 (kind); never starts Docker

🐳 Docker autostart  (start only; nothing is ever installed)
──────────────────────────────────────────────────────────────────
  If docker is installed but the daemon is stopped, ./tools/kind start tries to start it:
    macOS:   open -a Docker, then waits up to KIND_DOCKER_WAIT seconds (default 120), polling docker info.
```

Expected after a successful `./tools/kind start`: four `yes` preflight checks and a final line `Cluster: ai-ops-training`. The ports it chose are saved in `.logs/ports.env`.

## tools/ports.sh

Sourced by `tools/kind`, not run on its own. A port counts as busy when something listens on it (`lsof`, else `nc`), when a running container publishes it (`docker ps`), or when the same run already picked it. It writes the choices to `.logs/ports.env`.

## tools/build.sh

```bash
./tools/build.sh --help
./tools/build.sh --dir day-02-docker-basics/python-hello --dry-run build test
```

```text
build.sh: one central build script for every repo.

  build.sh [build] [test] [secure] [measure] [deploy] [docs] [--java|--gradle|--python|--node|--go|--dotnet] [--dir DIR] [--dry-run]

With no step names, runs: build test secure. The stack is auto-detected from the files in DIR
(default: current directory) unless a stack flag forces it.

Exit codes: 0 success, 1 a step failed, 2 usage error or stack not detected.
```

`--dry-run` prints the commands without running them. Pairs with `capstone/measure/measure.py` for the `measure` step.

## tools/deploy.sh

```bash
./tools/deploy.sh --help
COVERAGE=85 VULN_CRITICAL=0 VULN_HIGH=0 ./tools/deploy.sh registry.example/app:abc1234 --service demo --dry-run
```

```text
deploy.sh: ask the policy engine whether this deploy is allowed, then deploy with kubectl.

  deploy.sh IMAGE [--service NAME] [--namespace NS] [--dry-run]

Inputs it gathers (all can be overridden for tests):
  coverage        from reports/coverage.xml or reports/jacoco.xml   (override: COVERAGE)
  vulnerabilities from reports/trivy-fs.json or reports/trivy-image.json  (override: VULN_CRITICAL, VULN_HIGH)
  clock/timezone  now, in TIMEZONE (default UTC)                    (override: NOW_NS)
Policy: OPA_URL (an OPA server, e.g. http://opa.platform:8181) or, if unset, `opa eval` on POLICY_DIR.

Exit codes: 0 deployed (or allowed in dry run), 1 denied or deploy failed, 2 usage or missing input.
set -euo pipefail
```

By default it reads the policy from `day-15-guard-rails-and-opa/policies/`; set `POLICY_DIR` to use another folder.

## tools/check-docs-touched.sh

A CI gate for Day 28: `tools/check-docs-touched.sh [BASE_REF]` compares `BASE_REF...HEAD` (default `origin/main`, else `HEAD~1`). It passes when no code path changed, or at least one docs path changed, or a commit carries the trailer `Docs: n/a <reason>`; otherwise it exits 1. Its tests are in `day-28-write-good-docs/docs-as-code/tests/`.

## tools/coverage_percent.py

```bash
python3 tools/coverage_percent.py path/to/report.xml
```

Prints one number, for example `6.4`, taken from a Cobertura (`coverage.xml`) or JaCoCo (`jacoco.xml`) report.

## tools/versions.env

A plain list of `NAME=value` lines (image tags, chart versions, tool versions). Read it, or load it into a shell:

```bash
set -a; source tools/versions.env; set +a
echo "$KIND_VERSION"
```

```text
v0.27.0
```

Some entries float (`latest`); the file says which. Pin them after your first successful run.
