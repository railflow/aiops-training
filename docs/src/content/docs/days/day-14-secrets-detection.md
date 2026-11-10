---
title: "Day 14: Secrets, part 1: never commit them, and catch them when you do"
description: "Files in day-14-secrets-detection/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 14: Secrets, part 1: never commit them, and catch them when you do"
  order: 14
---

This page is the file-by-file guide to [`day-14-secrets-detection/`](https://github.com/railflow/aiops-training/tree/main/day-14-secrets-detection) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Why a committed secret is a permanent leak, why applications still need secrets, and how gitleaks, a pre-commit hook, and build.sh secure stop leaks.

Homework for this day is in [`day-14-secrets-detection/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-14-secrets-detection/homework.md) and is repeated at the bottom of this page.

## What is in the folder

5 files. Paths below are relative to the repo root unless noted.

### day-14-secrets-detection/secrets/

| File | What it is | How the lesson uses it |
|---|---|---|
| `secrets/gitleaks.toml` | Project gitleaks configuration (use with: gitleaks detect --config gitleaks.toml). | `cat day-14-secrets-detection/secrets/gitleaks.toml` |
| `secrets/pre-commit-config.yaml` | Same protection with the pre-commit framework (https://pre-commit.com): pip install pre-commit (or: brew install pre-commit) cp day-14-secrets-detection/secrets/pre-commit-config.yaml .pre-commit-config.yaml pre-commit install |  |
| `secrets/seed-demo.sh` | Creates a throwaway git repository that contains FAKE secrets, so scanners have something to find. | `day-14-secrets-detection/secrets/seed-demo.sh` |

### day-14-secrets-detection/secrets/hooks/

| File | What it is | How the lesson uses it |
|---|---|---|
| `secrets/hooks/pre-commit` | Local safety net: refuse to commit staged changes that contain secrets. | `cp day-14-secrets-detection/secrets/hooks/pre-commit .git/hooks/pre-commit` |

### day-14-secrets-detection/secrets/leaky-image/

| File | What it is | How the lesson uses it |
|---|---|---|
| `secrets/leaky-image/Dockerfile` | DO NOT DO THIS. Demonstrates why secrets must never be baked into an image. Build from a folder that contains a .env file you create in the lesson (fake values). | `cp day-14-secrets-detection/secrets/leaky-image/Dockerfile .` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
mkdir -p ~/heyjob-labs/day14/leaky && cd ~/heyjob-labs/day14/leaky
cp day-14-secrets-detection/secrets/leaky-image/Dockerfile .
echo "API_TOKEN=demo-token-not-real" > .env
docker build -t leaky:1 .
docker history --no-trunc leaky:1 | grep -E "DB_PASSWORD|API_TOKEN"
docker run --rm leaky:1 env | grep DB_PASSWORD
docker run --rm leaky:1 cat /app/.env
docker inspect leaky:1 --format '{{json .Config.Env}}'
```

```bash
day-14-secrets-detection/secrets/seed-demo.sh
cd ~/heyjob-labs/secrets-demo
git log --oneline
cat app/config.py
git log -p --all | grep -n "AKIA\|Sup3rS3cret"
```

```bash
cat day-14-secrets-detection/secrets/gitleaks.toml
gitleaks detect --source . --config day-14-secrets-detection/secrets/gitleaks.toml --redact; echo "exit code: $?"
```

```bash
cp day-14-secrets-detection/secrets/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo 'github_token = "demo-4f9a7c1e2b6d8035a1c4e7f90b2d6a38c7e1"' >> app/config.py
git add app/config.py
git commit -m "Add token"
echo "commit exit code: $?"
```

```bash
cd ~/aiops-training
sed -n '/^step_secure/,/^}/p' tools/build.sh
tools/build.sh --dir day-02-docker-basics/python-hello --dry-run secure
cd ~/heyjob-labs/secrets-demo && tools/build.sh --dir . --python secure; echo "exit code: $?"
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
<missing>  ...  /bin/sh -c #(nop)  ENV DB_PASSWORD=hunter2-demo-only
<missing>  ...  ARG API_TOKEN=demo-token-not-real
DB_PASSWORD=hunter2-demo-only
API_TOKEN=demo-token-not-real
["PATH=...","DB_PASSWORD=hunter2-demo-only"]
```

```text
Created /.../secrets-demo with 3 commits.
The current files are clean, but the secrets are still in the history (git log -p).
ad63eb8 Read credentials from the environment instead
2d013b8 Add application config
b4908ba Add README
```

## How these files relate to other days and shared tools

- Builds on [Day 4](/days/day-04-data-services-and-appwrite/), [Day 8](/days/day-08-security-and-supply-chain/), [Day 13](/days/day-13-ci-at-scale-build-sh/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).

## Homework

Work in `~/heyjob-labs/day14/`. Use only **fake** secrets, ever. The rest of the secrets homework (OpenBao, injection, rotation) is in Day 16.

### Exercise 1: Seed it and make the hook block it

**Do:** seed a fake AWS-style key and a fake password into a new file in a scratch repo, install the pre-commit hook, and capture the blocked commit.

### Exercise 2: `build.sh secure` fails, then passes

**Do:** run `build.sh secure` against the seeded repo (it must fail with exit code 1). Fix it for the **current tree** by moving the value to an environment variable, and re-run: the history scan still fails, so add a baseline for the existing finding and re-run.

### Exercise 3: False positive

**Do:** add a line to a test file containing the documented example value `AKIAIOSFODNN7EXAMPLE` (if your gitleaks version reports it) and allow it narrowly in a config file with a comment explaining why. Prove an unrelated fake key is **still** caught.

### Exercise 4: Recover and judge

**Do:** build the leaky image, recover the secret three ways, then write the corrected Dockerfile that reads the password at **runtime** (no `ENV`, no `COPY .env`). Prove with `docker history` and `docker run ... env` that the secret is gone.

### Exercise 5: Response plan

**Do:** write `leak-response.md`: the exact first five actions you take if an AWS key is found in a public repo, in order, and why rotation comes before history cleanup.
