---
title: "Day 28: Writing good docs (and keeping them true)"
description: "Files in day-28-write-good-docs/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 28: Writing good docs (and keeping them true)"
  order: 28
---

This page is the file-by-file guide to [`day-28-write-good-docs/`](https://github.com/railflow/aiops-training/tree/main/day-28-write-good-docs) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Docs as code with Starlight, the Diataxis framework, templates for runbooks and ADRs, AI-agent flows for drafting and reviewing, a CI gate that refuses code without docs, and deploying the docs site on your own cluster.

Homework for this day is in [`day-28-write-good-docs/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-28-write-good-docs/homework.md) and is repeated at the bottom of this page.

## What is in the folder

43 files. Paths below are relative to the repo root unless noted.

### day-28-write-good-docs/docs-as-code/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/cspell.json` | JSON data or configuration file. |  |
| `docs-as-code/style-guide.md` | Document: Documentation style guide |  |

### day-28-write-good-docs/docs-as-code/ai/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/ai/CLAUDE.md` | Document: CLAUDE.md (project memory for Claude Code) |  |
| `docs-as-code/ai/claude/settings.json` | JSON data or configuration file. |  |
| `docs-as-code/ai/claude/agents/docs-writer.md` | name: docs-writer |  |
| `docs-as-code/ai/claude/commands/doc-page.md` | description: Draft a new documentation page from a topic, following the style guide |  |
| `docs-as-code/ai/claude/commands/doc-review.md` | description: Review a docs change against the style guide and try to follow it literally |  |
| `docs-as-code/ai/claude/commands/doc-sync.md` | description: Compare the docs with the code and list or fix drift |  |
| `docs-as-code/ai/claude/hooks/docs-lint.sh` | Claude Code PostToolUse hook: after an edit to a docs file, warn about obvious problems (secret-looking strings, TODO/TBD). The hook receives the tool call as JSON on stdin (field names: check the Claude Code hooks docs for your version). |  |
| `docs-as-code/ai/claude/skills/write-runbook/SKILL.md` | Document: Write a runbook |  |
| `docs-as-code/ai/cursor-rules/docs.mdc` | Support file. |  |

### day-28-write-good-docs/docs-as-code/app-docs-template/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/app-docs-template/README.md` | Document: __APP__ |  |
| `docs-as-code/app-docs-template/docs/api.md` | Document: __APP__ API |  |
| `docs-as-code/app-docs-template/docs/architecture.md` | Document: __APP__ architecture |  |
| `docs-as-code/app-docs-template/docs/runbook.md` | Document: __APP__ runbook |  |
| `docs-as-code/app-docs-template/docs/adr/0000-template.md` | Document: NNNN. Title in the form of a decision |  |
| `docs-as-code/app-docs-template/docs/adr/0001-record-architecture-decisions.md` | Document: 0001. Record architecture decisions |  |

### day-28-write-good-docs/docs-as-code/ci/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/ci/docs-freshness.yaml` | Weekly: ask an AI agent to compare docs with code and open an ISSUE (never push to main) listing drift. |  |
| `docs-as-code/ci/docs.yaml` | Copy to .forgejo/workflows/docs.yaml. On pull requests: the docs gate, a docs build and the link check. |  |

### day-28-write-good-docs/docs-as-code/deploy/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/deploy/Dockerfile` | Example docs site image (the Starlight project in day-28-write-good-docs/docs-as-code/starlight-site/; the course site itself is Next.js): | `docker build -f day-28-write-good-docs/docs-as-code/deploy/Dockerfile -t docs-site:1.0 .` |
| `docs-as-code/deploy/Dockerfile.dockerignore` | Files kept out of the Docker build context. |  |
| `docs-as-code/deploy/gatus-endpoint.yaml` | Add under `endpoints:` in the Gatus config (Day 21). |  |
| `docs-as-code/deploy/nginx.conf` | Static docs site. Runs as the non-root nginx user (101) on 8080 with a read-only root filesystem: the pid file and all temp paths live in /tmp (mount an emptyDir there). Logs are JSON on stdout for the collector. |  |
| `docs-as-code/deploy/flux/docs-sync.yaml` | In the config repo: apps/docs/ holds a copy of ../k8s/docs.yaml (with the image tag CI updates). Flux applies it. Defines: Kustomization. |  |
| `docs-as-code/deploy/k8s/docs.yaml` | Docs site on the cluster at http://docs.localhost:8080. Image built from deploy/Dockerfile and loaded into kind or pushed to Nexus. Defines: Namespace `docs`, Deployment, Service, IngressRoute and 1 more. | `kubectl apply -f day-28-write-good-docs/docs-as-code/deploy/k8s/docs.yaml` |

### day-28-write-good-docs/docs-as-code/starlight-site/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/starlight-site/.gitignore` | Files git should not track for this folder. |  |
| `docs-as-code/starlight-site/README.md` | Document: Example docs site (Starlight) |  |
| `docs-as-code/starlight-site/astro.config.mjs` | @ts-check |  |
| `docs-as-code/starlight-site/package-lock.json` | Dependency lockfile generated by the package manager; do not edit by hand. |  |
| `docs-as-code/starlight-site/package.json` | Node project manifest for docs-as-code-example. Scripts: dev, start, build, preview, astro. |  |
| `docs-as-code/starlight-site/tsconfig.json` | TypeScript compiler settings. |  |
| `docs-as-code/starlight-site/public/favicon.svg` | Image. |  |
| `docs-as-code/starlight-site/src/content.config.ts` | TypeScript/JavaScript source file. |  |
| `docs-as-code/starlight-site/src/assets/logo-dark.svg` | Image. |  |
| `docs-as-code/starlight-site/src/assets/logo-light.svg` | Image. |  |
| `docs-as-code/starlight-site/src/content/docs/index.mdx` | Document: What is here |  |
| `docs-as-code/starlight-site/src/content/docs/how-to/roll-back-a-deploy.md` | Document: Steps |  |
| `docs-as-code/starlight-site/src/content/docs/reference/service-reference.md` | Document: Endpoints |  |
| `docs-as-code/starlight-site/src/content/docs/start/overview.md` | Document: Organisation |  |
| `docs-as-code/starlight-site/src/content/docs/start/why-docs-as-code.md` | title: Why docs live in git |  |
| `docs-as-code/starlight-site/src/styles/custom.css` | Support file. |  |

### day-28-write-good-docs/docs-as-code/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `docs-as-code/tests/test-check-docs-touched.sh` | Tests for tools/check-docs-touched.sh against throwaway git repositories. No network, no installs. | `day-28-write-good-docs/docs-as-code/tests/test-check-docs-touched.sh` |
| `docs-as-code/tests/test-docs-image-context.sh` | Checks the docs image build path without Docker: every COPY source in deploy/Dockerfile exists and is not excluded by Dockerfile.dockerignore, the lockfile matches package.json, and a fake `docker` on PATH records the command from Day 28. |  |

## Files this day uses from other folders

From [Day 10](/days/day-10-local-platform/): `day-10-local-platform/` (`platform/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```powershell
cd day-28-write-good-docs/docs-as-code/starlight-site
npm ci
Set-Content src/content/docs/reference/my-first-page.md "---`ntitle: My first page`ndescription: A test page.`n---`n`nHello from docs-as-code.`n"
npm run dev          # leave running, open http://localhost:4321/reference/my-first-page/
```

```bash
cd day-28-write-good-docs/docs-as-code/starlight-site
npm ci
printf -- '---\ntitle: My first page\ndescription: A test page.\n---\n\nHello from docs-as-code.\n' > src/content/docs/reference/my-first-page.md
npm run dev          # leave running, open http://localhost:4321/reference/my-first-page/
```

```bash
cd day-10-local-platform/platform
./platform new orders-api --dir /tmp/apps
ls /tmp/apps/orders-api/docs /tmp/apps/orders-api/docs/adr
```

```bash
day-28-write-good-docs/docs-as-code/tests/test-check-docs-touched.sh
```

```bash
cd ~/aiops-training
docker build -f day-28-write-good-docs/docs-as-code/deploy/Dockerfile -t docs-site:1.0 .
docker images docs-site:1.0
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
astro v7.x ready in 600 ms
Local   http://localhost:4321/
```

```text
created /tmp/apps/orders-api
/tmp/apps/orders-api/docs:
adr  api.md  architecture.md  runbook.md
```

## How these files relate to other days and shared tools

- Builds on [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 21](/days/day-21-is-my-app-up-gatus/), [Day 22](/days/day-22-progressive-delivery-flux-flagger/), [Day 25](/days/day-25-internal-platform/) (cluster, images or secrets created there).
- Uses [`tools/check-docs-touched.sh`](/tools/) (for example from `day-28-write-good-docs/docs-as-code/tests/test-check-docs-touched.sh`).
- Refers to files in [Capstone](/days/capstone/) (for example from `day-28-write-good-docs/docs-as-code/deploy/Dockerfile.dockerignore`).
- The lesson also uses files from [Day 10](/days/day-10-local-platform/).

## Homework

Deliverables go in `~/heyjob-labs/day28/`. Each has a self-check.

### Exercise 1: Classify
**Do:** take five pages of this course (or your own repo) and label each as tutorial, how-to, reference or explanation; for any that mix types, say how you would split them.
### Exercise 2: Break a link on purpose
**Do:** in `day-28-write-good-docs/docs-as-code/starlight-site/` (or your own site, after adding `starlight-links-validator`) break an internal link, run `npm run build`, read the report, fix it.
### Exercise 3: A real runbook
**Do:** write the runbook for one of your own services from `app-docs-template/docs/runbook.md`. Give it to a colleague (or an agent with `/doc-review`) and ask them to follow it literally.
### Exercise 4: Three ADRs
**Do:** write three short ADRs for decisions already made (a database choice, a base image, a deployment tool).
### Exercise 5: Tame an agent
**Do:** have an agent write a how-to page with `/doc-page`. Then find **three** things it got wrong or could not know (a flag, a version, a path).
### Exercise 6: The gate in your repo
**Do:** copy `check-docs-touched.sh` into a repository you own and wire it as a required check on pull requests. Open one pull request that fails and one that passes.
### Exercise 7: Deploy the docs
**Do:** build the example docs image (or one from your own site), run it on the cluster at `docs.localhost:8080`, add the Gatus check, and read three JSON log lines from `kubectl -n docs logs deploy/docs`.
### Exercise 8: Freshness
**Do:** run `doc-sync` against your repository by hand (not in CI).
