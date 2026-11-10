---
title: "Day 1: Getting started"
description: "Files in day-01-getting-started/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 1: Getting started"
  order: 1
---

This page is the file-by-file guide to [`day-01-getting-started/`](https://github.com/railflow/aiops-training/tree/main/day-01-getting-started) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Start from a bare Mac or Windows PC, then install Homebrew or winget, install Docker Desktop and get the daemon running, clone the repo, run ./tools/kind start (and watch it fail on purpose), install kind, kubectl, and friends, install Claude Code, and get a local Kubernetes cluster running.

Homework for this day is in [`day-01-getting-started/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-01-getting-started/homework.md) and is repeated at the bottom of this page.

## What is in the folder

This day has no sample files of its own. The folder holds the homework and a README only. The lesson uses files from other folders, listed below.

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/`.

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

This day has no commands that run files from this repository; it is explained in the lesson. See the homework below for what to run.

## Expected output

Each command should finish without an error. If one exits non-zero, check the earlier commands first and compare with the lesson on the course site.

## How these files relate to other days and shared tools

- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- Files from this folder are used by [Day 2](/days/day-02-docker-basics/).

## Homework

Work in `~/heyjob-labs/day01/`. Commit after every exercise.

### Exercise 1: Get `./tools/kind start` to succeed

**Do:** run `./tools/kind start` until it succeeds and capture the plain-text output.

```bash
cd ~/aiops-training
NO_COLOR=1 ./tools/kind start 2>&1 | tee ~/heyjob-labs/day01/start-output.txt
```

**Deliverable:** `day01/start-output.txt` with four "yes" checks and the final "Cluster: ai-ops-training" line.

### Exercise 2: Run the full lifecycle

**Do:** run `stop`, `list`, `docker ps -a`, `start`, `destroy`, `list` in order, saving each output to `day01/*.txt` with `tee`, then recreate the cluster with `./tools/kind start`. Write `day01/notes.md` with three sentences: (1) after `stop`, was the cluster still listed and why; (2) after restart, was the busybox pod still there and why; (3) what does `destroy` remove that `stop` does not.

### Exercise 3: Tool tour

**Do:** with the cluster running, in k9s type `:pods`, select the busybox pod, press `d` (describe) then `Esc`, `l` for logs, quit with `:q`. Open lazydocker and look at the node container's logs and stats. Start `claude` in `~/aiops-training` and ask it to explain what the kind node container is in 5 bullets (no edits).

**Deliverable:** `day01/tools.md`: one line per tool (k9s, lazydocker, Docker Desktop, your terminal, Claude Code) on what you used it for and what you liked, plus Claude's 5 bullets and whether you agree.

### Exercise 4: Break it on purpose

**Do:** quit Docker Desktop, run `NO_COLOR=1 ./tools/kind list 2>&1 | tee ~/heyjob-labs/day01/docker-down.txt`, restart Docker Desktop, and re-run `./tools/kind list`.

**Deliverable:** `docker-down.txt` plus two lines appended to `notes.md`: which check failed and which hint applied.
