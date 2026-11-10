---
title: "Day 8: Vulnerabilities and the software supply chain"
description: "Files in day-08-security-and-supply-chain/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 8: Vulnerabilities and the software supply chain"
  order: 8
---

This page is the file-by-file guide to [`day-08-security-and-supply-chain/`](https://github.com/railflow/aiops-training/tree/main/day-08-security-and-supply-chain) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Scan images with Trivy, read the report, fix what is fixable, produce SBOMs in CycloneDX and SPDX, and sign and attest an image.

Homework for this day is in [`day-08-security-and-supply-chain/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-08-security-and-supply-chain/homework.md) and is repeated at the bottom of this page.

## What is in the folder

6 files. Paths below are relative to the repo root unless noted.

### day-08-security-and-supply-chain/security/fixed/

| File | What it is | How the lesson uses it |
|---|---|---|
| `security/fixed/Dockerfile` | Container image recipe (base `python:3.12-slim`). | `diff day-08-security-and-supply-chain/security/vulnerable/Dockerfile day-08-security-and-supply-chain/security/fixed/Dockerfile` |
| `security/fixed/app.py` | Python module. Defines: `index`. |  |
| `security/fixed/requirements.txt` | Pinned Python dependencies for this folder. | `diff day-08-security-and-supply-chain/security/vulnerable/requirements.txt day-08-security-and-supply-chain/security/fixed/requirements.txt` |

### day-08-security-and-supply-chain/security/vulnerable/

| File | What it is | How the lesson uses it |
|---|---|---|
| `security/vulnerable/Dockerfile` | Deliberately OLD base image and dependencies so the scanner has something to find. Never deploy this. If the tag has been removed from Docker Hub, pick any old python:3.x-slim tag. | `cat day-08-security-and-supply-chain/security/vulnerable/Dockerfile` |
| `security/vulnerable/app.py` | Python module. Defines: `index`. |  |
| `security/vulnerable/requirements.txt` | Pinned Python dependencies for this folder. | `diff day-08-security-and-supply-chain/security/vulnerable/requirements.txt day-08-security-and-supply-chain/security/fixed/requirements.txt` |

## Files this day uses from other folders

From [Day 3](/days/day-03-kind-kubernetes/): `day-03-kind-kubernetes/` (`k8s/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ~/aiops-training
cat day-08-security-and-supply-chain/security/vulnerable/Dockerfile
docker build -t vuln-demo:1.0 day-08-security-and-supply-chain/security/vulnerable
trivy image --severity HIGH,CRITICAL vuln-demo:1.0
```

```bash
diff day-08-security-and-supply-chain/security/vulnerable/Dockerfile day-08-security-and-supply-chain/security/fixed/Dockerfile
diff day-08-security-and-supply-chain/security/vulnerable/requirements.txt day-08-security-and-supply-chain/security/fixed/requirements.txt
docker build -t vuln-demo:2.0 day-08-security-and-supply-chain/security/fixed
trivy image --severity HIGH,CRITICAL vuln-demo:2.0 | grep -E "Total|Report Summary"
```

```bash
trivy fs --scanners vuln,secret day-08-security-and-supply-chain/security/vulnerable
trivy config day-03-kind-kubernetes/k8s
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
vuln-demo:1.0 (debian 10.13)
============================
Total: 85 (HIGH: 70, CRITICAL: 15)

┌──────────────┬───────────────┬──────────┬──────────────┬───────────────────┬───────────────┐
│   Library    │ Vulnerability │ Severity │    Status    │ Installed Version │ Fixed Version │
├──────────────┼───────────────┼──────────┼──────────────┼───────────────────┼───────────────┤
│ libssl1.1    │ CVE-20XX-XXXX │ CRITICAL │ fixed        │ 1.1.1n-0+deb10u3  │ 1.1.1n-...    │
...
Python (python-pkg)
Total: 12 (HIGH: 9, CRITICAL: 3)
│ Flask        │ CVE-20XX-XXXX │ HIGH     │ fixed        │ 1.1.2             │ 2.2.5         │
```

```text
Total: 3 (HIGH: 3, CRITICAL: 0)
```

## How these files relate to other days and shared tools

- Builds on [Day 2](/days/day-02-docker-basics/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 3](/days/day-03-kind-kubernetes/).
- Files from this folder are used by [Day 11](/days/day-11-first-ci-and-kubectl/), [Day 15](/days/day-15-guard-rails-and-opa/), [Day 23](/days/day-23-server-and-application-patching/).

## Homework

Work in `~/heyjob-labs/day08/`.

### Exercise 1: Before and after

**Do:** scan `vuln-demo:1.0` and `vuln-demo:2.0` (HIGH and CRITICAL). Write `before-after.md` with both totals, the base images, and the three changes that mattered most.

### Exercise 2: Scan your own apps

**Do:** scan `hello-py-app:1.1` and `hello-java-app:1.1` from Day 6. Pick the worst finding for each and write what you would change. Do not change anything yet.

### Exercise 3: Two SBOMs

**Do:** generate CycloneDX and SPDX SBOMs for one of your apps and answer, with `jq`, "which version of `<some package>` is inside?" from each.

### Exercise 4: Signed and attested

**Do:** sign one of your app images by digest, attach its SBOM, and capture a successful verify and a failed verify (after altering the image).
