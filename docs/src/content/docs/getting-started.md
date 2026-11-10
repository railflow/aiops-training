---
title: Getting started
description: "Git settings, Docker, kind, kubectl, and the working directory for the aiops-training repo."
sidebar:
  order: 1
---

The lessons on the course site walk through installing everything step by step (Day 1). This page is the short checklist for working with the repo.

## 1. Git settings and cloning

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.autocrlf input
cd ~
git clone https://github.com/railflow/aiops-training
cd aiops-training
```

Set `core.autocrlf input` **before** cloning on Windows. The repo's `.gitattributes` already forces LF line endings for scripts and Dockerfiles; CRLF in a shell script fails with `bash\r: No such file or directory`.

## 2. Tools you need

| Tool | Used for | Check it |
|---|---|---|
| git | cloning, your own commits | `git --version` |
| Docker (Docker Desktop, or Docker Engine on Linux) | building images, running kind | `docker info` |
| kind | the local Kubernetes cluster `ai-ops-training` | `kind version` (the course pins the version in `tools/versions.env`) |
| kubectl | talking to the cluster | `kubectl version --client` |
| bash | every script here is bash; on Windows use Git Bash or WSL2 (Ubuntu) | `bash --version` |
| Node.js 22.23.4 or newer | only for building these docs with `./build.sh` | `node --version` |

Later days add more tools (helm, jq, k6, opa, gitleaks, and so on). Each day's page and the lesson say when. Nothing in this repo installs software for you.

## 3. The working directory

- Clone to `~/aiops-training` and run the commands **from the repo root** unless a command starts with `cd`.
- Do your homework in a **separate** folder (`~/heyjob-labs/dayNN/`), in your own git repository. Copy example files from this repo into it; do not edit this clone.
- Scripts write their own notes to `.logs/` (for example the ports `tools/kind` picked). That folder is git-ignored.

## 4. First cluster

```bash
./tools/kind start
kubectl get nodes
```

`./tools/kind start` checks Docker, kubectl and kind, creates the cluster `ai-ops-training`, and deploys a small busybox pod. `./tools/kind stop` keeps the cluster, `./tools/kind destroy` deletes it. Details: [shared tools](/tools/).

## 5. Reading these docs

From the repo root: `./build.sh` builds them and serves them on `http://localhost:4321/`. The root README lists every option.
