---
title: "Day 15: Guard rails and policy as code with OPA"
description: "Files in day-15-guard-rails-and-opa/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 15: Guard rails and policy as code with OPA"
  order: 15
---

This page is the file-by-file guide to [`day-15-guard-rails-and-opa/`](https://github.com/railflow/aiops-training/tree/main/day-15-guard-rails-and-opa) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Start with a coverage gate in a workflow, see why it does not scale, then express deploy rules (coverage, deploy window, vulnerabilities) in Rego, test them, run OPA on kind, and gate deploys with deploy.sh.

Homework for this day is in [`day-15-guard-rails-and-opa/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-15-guard-rails-and-opa/homework.md) and is repeated at the bottom of this page.

## What is in the folder

8 files. Paths below are relative to the repo root unless noted.

### day-15-guard-rails-and-opa/policies/

| File | What it is | How the lesson uses it |
|---|---|---|
| `policies/coverage.rego` | OPA policy written in Rego. | `--from-file=coverage.rego=day-15-guard-rails-and-opa/policies/coverage.rego \` |
| `policies/deploy_test.rego` | Automated tests for deploy. |  |
| `policies/main.rego` | OPA policy written in Rego. | `--from-file=main.rego=day-15-guard-rails-and-opa/policies/main.rego \` |
| `policies/opa.yaml` | OPA running as an HTTP decision service in the cluster. Policies come from the ConfigMap "opa-policies" which you create from the .rego files (see the lesson), never by hand-editing here. Defines: Deployment, Service. | `kubectl apply -f day-15-guard-rails-and-opa/policies/opa.yaml` |
| `policies/sample-input-allowed.json` | JSON data or configuration file. | `opa eval --format pretty -d day-15-guard-rails-and-opa/policies -i day-15-guard-rails-and-opa/policies/sample-input-allowed.json 'data.deploy.decis...` |
| `policies/sample-input-denied.json` | JSON data or configuration file. | `cat day-15-guard-rails-and-opa/policies/sample-input-denied.json` |
| `policies/vulnerabilities.rego` | OPA policy written in Rego. | `--from-file=vulnerabilities.rego=day-15-guard-rails-and-opa/policies/vulnerabilities.rego` |
| `policies/window.rego` | OPA policy written in Rego. | `--from-file=window.rego=day-15-guard-rails-and-opa/policies/window.rego \` |

## Files this day uses from other folders

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ~/aiops-training
tools/build.sh --dir day-04-data-services-and-appwrite/java-app test
python3 tools/coverage_percent.py day-04-data-services-and-appwrite/java-app/reports/jacoco.xml
```

```bash
cd day-15-guard-rails-and-opa/policies
ls
cat main.rego coverage.rego
```

```bash
cd ~/aiops-training
cat day-15-guard-rails-and-opa/policies/sample-input-denied.json
opa eval --format pretty -d day-15-guard-rails-and-opa/policies -i day-15-guard-rails-and-opa/policies/sample-input-allowed.json 'data.deploy.decision'
opa eval --format pretty -d day-15-guard-rails-and-opa/policies -i day-15-guard-rails-and-opa/policies/sample-input-denied.json  'data.deploy.decision'
```

```bash
cd ~/aiops-training
opa fmt --diff day-15-guard-rails-and-opa/policies
opa check --strict day-15-guard-rails-and-opa/policies
opa test -v day-15-guard-rails-and-opa/policies
opa test --coverage day-15-guard-rails-and-opa/policies | head -20
```

```bash
cd ~/aiops-training
kubectl create configmap opa-policies -n platform \
--from-file=main.rego=day-15-guard-rails-and-opa/policies/main.rego \
--from-file=coverage.rego=day-15-guard-rails-and-opa/policies/coverage.rego \
--from-file=window.rego=day-15-guard-rails-and-opa/policies/window.rego \
--from-file=vulnerabilities.rego=day-15-guard-rails-and-opa/policies/vulnerabilities.rego
kubectl apply -f day-15-guard-rails-and-opa/policies/opa.yaml
kubectl -n platform rollout status deploy/opa --timeout=120s
kubectl -n platform port-forward svc/opa 8181:8181 &
sleep 2
curl -s localhost:8181/health
curl -s -X POST localhost:8181/v1/data/deploy/decision -H 'Content-Type: application/json' \
-d "{\"input\": $(cat day-15-guard-rails-and-opa/policies/sample-input-denied.json)}" | jq .
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
==> done: test succeeded
6.4
```

```text
{
  "allow": true,
  "reasons": []
}
{
  "allow": false,
  "reasons": [
    "1 CRITICAL and 3 HIGH vulnerabilities found; fix or accept them first",
    "coverage 6.4% is below the required 80%",
    "outside the deploy window (Wednesday 20:00-22:00 America/Los_Angeles); it is Thursday 21:00 there"
  ]
}
```

## How these files relate to other days and shared tools

- Builds on [Day 8](/days/day-08-security-and-supply-chain/), [Day 9](/days/day-09-build-tools-and-tests/), [Day 13](/days/day-13-ci-at-scale-build-sh/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 4](/days/day-04-data-services-and-appwrite/).

## Homework

Work in `~/heyjob-labs/day15/`.

### Exercise 1: Three tested policies

**Do:** copy `day-15-guard-rails-and-opa/policies/` into your own `policies/` folder. Add a **fourth** rule of your choice (for example: only deploy images from your registry host, or deny the tag `latest`) with at least two tests (one allow, one deny).

### Exercise 2: Prove each rule blocks

**Do:** with `deploy.sh` and the OPA service (or `opa eval`), produce three denied runs, one for each original rule individually (only one input wrong each time), plus one allowed run. Save the four transcripts.

### Exercise 3: Time travel

**Do:** with `NOW_NS`, show the deploy allowed at Wednesday 20:00 PST, Wednesday 21:59 PST, and denied at Wednesday 22:00 PST and Wednesday 19:59 PST (compute the nanosecond values with `python3` and `zoneinfo`).

### Exercise 4: Exceptions with an expiry

**Do:** extend the coverage rule so a service named in `data.exceptions` (a JSON file with `{"hello-java": {"min_coverage": 5, "expires": "2027-01-01"}}`) uses its own lower threshold until the expiry date. Add tests for before and after the expiry.

### Exercise 5: Why not just a script?

**Do:** write 6-8 sentences: for a company with 1,000 repos, why is a central policy service better than a shared shell function? Cover testing, audit, exceptions, ownership, and the risk of a policy service outage.
