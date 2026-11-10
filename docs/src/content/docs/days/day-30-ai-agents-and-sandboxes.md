---
title: "Day 30: Agents and sandboxes"
description: "Files in day-30-ai-agents-and-sandboxes/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 30: Agents and sandboxes"
  order: 30
---

This page is the file-by-file guide to [`day-30-ai-agents-and-sandboxes/`](https://github.com/railflow/aiops-training/tree/main/day-30-ai-agents-and-sandboxes) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: How coding agents actually work, why they need a sandbox that is not your CI, the options for running them safely, packaging skills like software, and making agents check each other.

Homework for this day is in [`day-30-ai-agents-and-sandboxes/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-30-ai-agents-and-sandboxes/homework.md) and is repeated at the bottom of this page.

## What is in the folder

This day has no sample files of its own. The folder holds the homework and a README only. The lesson uses files from other folders, listed below.

## Files this day uses from other folders

From [Day 29](/days/day-29-ai-tools-foundations/): `day-29-ai-tools-foundations/` (`ai-devex/`).

#### day-29-ai-tools-foundations/ai-devex/

| File | What it is | How the lesson uses it |
|---|---|---|
| `.gitignore` | Files git should not track for this folder. |  |
| `README.md` | Document: day-29-ai-tools-foundations/ai-devex |  |
| `requirements.txt` | Pinned Python dependencies for this folder. |  |
| `decision/captured-output.txt` | Text file (sample data or captured output). |  |
| `decision/classify.py` | Turn Jev's per-question probabilities into one flaky probability and readable reasons. The weights are ours, a starting point to tune on labelled data. |  |
| `decision/dataset.jsonl` | Sample data file with fictional values. |  |
| `decision/evaluate.py` | Score a decision backend on the labelled dataset and show what thresholds buy you. |  |
| `decision/make_dataset.py` | Generate a SYNTHETIC labelled dataset of failing CI test runs: |  |
| `evals/captured-output.txt` | Text file (sample data or captured output). |  |
| `evals/run_evals.py` | A deliberately small eval harness: tasks.json, deterministic checks (no LLM judge), N repeats, a per-model table. |  |
| `evals/tasks.json` | JSON data or configuration file. |  |
| `gateway/ask.py` | Ask one or more models the same question through an OpenAI-compatible gateway and compare answer, latency and cost. |  |
| `incident-to-pr/.gitignore` | Files git should not track for this folder. |  |
| `incident-to-pr/captured-output.txt` | Text file (sample data or captured output). |  |
| `incident-to-pr/pipeline.py` | POST /api/v1/repos/&#123;owner&#125;/&#123;repo&#125;/pulls. The branch must already be pushed. Not run against a real Forgejo by the author; see tests (fake server). |  |
| `incident-to-pr/fixtures/alert.json` | JSON data or configuration file. |  |
| `incident-to-pr/fixtures/context.json` | JSON data or configuration file. |  |
| `incident-to-pr/sample-app/conftest.py` | Python module. |  |
| `incident-to-pr/sample-app/pricing.py` | Python module. Defines: `apply_discount`, `total`. |  |
| `incident-to-pr/sample-app/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `incident-to-pr/sample-app/tests/test_pricing.py` | Automated tests for pricing. |  |
| `lib/llm.py` | One tiny OpenAI-compatible chat client (stdlib only) so every lab talks to a gateway the same way. |  |
| `metrics/001_ai_tables.sql` | Outcome metrics for AI-assisted work. One row per change (PR); one row per incident; one row per test per day. |  |
| `metrics/queries.sql` | name: lead_time_hours_by_author |  |
| `sandbox/bad-job.yaml` | Every classic mistake in one Job. check_job.py should flag all of them. Defines: Job. |  |
| `sandbox/captured-output.txt` | Text file (sample data or captured output). |  |
| `sandbox/check_job.py` | Lint a Kubernetes manifest (Job + NetworkPolicy) for the properties an agent sandbox needs. |  |
| `sandbox/good-job.yaml` | A sandbox Job for an untrusted agent: no privileges, no host access, no cluster API token, no network except what the policy allows. Defines: Job, NetworkPolicy. |  |
| `skills/captured-output.txt` | Text file (sample data or captured output). |  |
| `skills/check_skills.py` | CI guard rails for a skills registry: every skill is a folder with SKILL.md. |  |
| `skills/examples/bad-skill/SKILL.md` | name: Helper |  |
| `skills/examples/write-runbook/SKILL.md` | Document: Write a runbook |  |
| `skills/examples/write-runbook/templates/runbook.md` | Document: Runbook: &lt;alert&gt; |  |
| `specs/captured-output.txt` | Text file (sample data or captured output). |  |
| `specs/check_spec.py` | Lint a spec file so an agent never starts from a vague one. Exit 0 = ok, 1 = problems (printed one per line). Usage: check_spec.py SPEC.md [SPEC.md ...] Wire it into CI for any path under specs/ or docs/specs/. |  |
| `specs/spec-template.md` | Document: Problem |  |
| `specs/examples/bad.md` | Document: Problem |  |
| `specs/examples/good.md` | Document: Problem |  |
| `tests/conftest.py` | Python module. Defines: `_H`, `fake_server`. |  |
| `tests/test_decision.py` | Automated tests for decision. |  |
| `tests/test_evals.py` | Automated tests for evals. |  |
| `tests/test_gateway.py` | Automated tests for gateway. |  |
| `tests/test_incident_to_pr.py` | Automated tests for incident to pr. |  |
| `tests/test_metrics_sql.py` | Every table and query in metrics/, run on embedded ClickHouse (chdb) with seeded rows. Skips without chdb. |  |
| `tests/test_sandbox.py` | Automated tests for sandbox. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-29-ai-tools-foundations/ai-devex
pip install pyyaml            # inside your venv from Day 29
python3 sandbox/check_job.py sandbox/good-job.yaml sandbox/bad-job.yaml
```

```bash
cd day-29-ai-tools-foundations/ai-devex
python3 skills/check_skills.py skills/examples
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
sandbox/good-job.yaml: no errors
sandbox/bad-job.yaml: ERROR hostNetwork is true
sandbox/bad-job.yaml: ERROR automountServiceAccountToken must be false (the agent does not need the cluster API)
sandbox/bad-job.yaml: ERROR volume 'sock' is a hostPath (/var/run/docker.sock): host access
sandbox/bad-job.yaml: ERROR container 'agent' is privileged
sandbox/bad-job.yaml: ERROR container 'agent' mounts docker.sock: that is root on the node
sandbox/bad-job.yaml: ERROR container 'agent': env OPENROUTER_API_KEY has a literal value that looks like a secret; use secretKeyRef
sandbox/bad-job.yaml: ERROR no NetworkPolicy restricting Egress for the sandbox pods
```

```text
skills/examples/bad-skill/SKILL.md: ERROR name 'Helper' must be lowercase-with-hyphens
skills/examples/bad-skill/SKILL.md: ERROR name 'Helper' does not match its folder 'bad-skill'
skills/examples/bad-skill/SKILL.md: ERROR description under 40 characters: the agent picks skills by description, so say what it does and WHEN to use it
skills/examples/bad-skill/SKILL.md: ERROR looks like it contains a secret
skills/examples/bad-skill/SKILL.md: ERROR pipes a download into a shell
skills/examples/bad-skill/SKILL.md: ERROR prompt-injection phrase
skills/examples/bad-skill/SKILL.md: ERROR asks the agent to hide actions from the user
skills/examples/bad-skill/SKILL.md: warn  no 'owner' in front matter (needed for curation and pruning)
skills/examples/bad-skill/SKILL.md: warn  no 'version' in front matter (needed for curation and pruning)
skills/examples/write-runbook/SKILL.md: ok
```

## How these files relate to other days and shared tools

- Builds on [Day 5](/days/day-05-kubernetes-jobs/), [Day 6](/days/day-06-networking-and-network-policy/), [Day 8](/days/day-08-security-and-supply-chain/), [Day 14](/days/day-14-secrets-detection/), [Day 15](/days/day-15-guard-rails-and-opa/), [Day 27](/days/day-27-durable-workflows-temporal/), [Day 29](/days/day-29-ai-tools-foundations/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 29](/days/day-29-ai-tools-foundations/).
- Files from this folder are used by [Day 36](/days/day-36-cloud-agent-sandboxes/).

## Homework

**Design a sandbox for your company.** In one to two pages, with a Mermaid diagram:

1. Pick a pattern from the decision table for each of: (a) a public open-source repo, (b) an internal service repo, (c) a repo that processes customer data. Justify with the questions in the table.
2. List what each sandbox may reach (network destinations, secrets, repos) and how each is enforced. Name the per-run token and its scope.
3. Say how the sandbox is started, watched and killed (Temporal, the bus, a Job controller) and what happens if the orchestrator dies.
4. List five ways it could still fail, and for each a detection or a limit.
5. Describe the skills registry for your team: owners, review, prune policy and the CI checks you would add beyond `check_skills.py`.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Pattern choice** | One pattern for everything | Pattern per risk level | Justified by data sensitivity, hostile-input risk and what you can operate; admits what you cannot get (for example KVM) |
| **Isolation detail** | "Use a container" | Network, secrets, filesystem, identity each addressed | Each control has an enforcement point (policy, manifest, runtime) and a test or lint |
| **Failure thinking** | Happy path | Several failures listed | Residual risk stated honestly; detection and kill switch described |
| **Skills** | Not covered | Owners and CI checks | Prune policy with usage data, supply-chain stance, human review step |
| **Honesty** | Vendor claims repeated | Sources cited | Separates "documented", "we ran it" and "we assume" |
