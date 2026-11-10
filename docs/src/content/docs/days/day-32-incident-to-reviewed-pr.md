---
title: "Day 32: From incident to reviewed PR"
description: "Files in day-32-incident-to-reviewed-pr/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 32: From incident to reviewed PR"
  order: 32
---

This page is the file-by-file guide to [`day-32-incident-to-reviewed-pr/`](https://github.com/railflow/aiops-training/tree/main/day-32-incident-to-reviewed-pr) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: A graded exercise that chains an alert, ClickHouse context, decision-model triage, a fix agent, coverage measurement, a pull request, an independent reviewer on a different model and a human gate.

Homework for this day is in [`day-32-incident-to-reviewed-pr/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-32-incident-to-reviewed-pr/homework.md) and is repeated at the bottom of this page.

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
| `incident-to-pr/pipeline.py` | POST /api/v1/repos/&#123;owner&#125;/&#123;repo&#125;/pulls. The branch must already be pushed. Not run against a real Forgejo by the author; see tests (fake server). | `python3 pipeline.py --approve-as dana` |
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
pip install -r requirements.txt           # in your venv from Day 29; includes pytest-cov
cd incident-to-pr/sample-app && python -m pytest -q; cd ..
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
FAILED tests/test_pricing.py::test_discount_is_whole_cents - assert 1699.15 =...
1 failed, 2 passed
```

## How these files relate to other days and shared tools

- Builds on [Day 20](/days/day-20-alerting-with-keep/), [Day 27](/days/day-27-durable-workflows-temporal/), [Day 29](/days/day-29-ai-tools-foundations/), [Day 30](/days/day-30-ai-agents-and-sandboxes/), [Day 31](/days/day-31-ai-quality-specs-evals-decisions/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 29](/days/day-29-ai-tools-foundations/).

## Homework

Build the pipeline for **one real class of incident in your own system** (not the sample app), replacing at least four of the nine stand-ins in the table. Submit the repo, a recorded run (`run.jsonl` and `metrics.json`) and a two-page write-up.
