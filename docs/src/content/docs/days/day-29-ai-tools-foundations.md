---
title: "Day 29: AI tools for DevEx, foundations"
description: "Files in day-29-ai-tools-foundations/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 29: AI tools for DevEx, foundations"
  order: 29
---

This page is the file-by-file guide to [`day-29-ai-tools-foundations/`](https://github.com/railflow/aiops-training/tree/main/day-29-ai-tools-foundations) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: A filter for shiny things, outcome metrics instead of token counts, models and tiers, and AI gateways with a hands-on OpenRouter lab.

Homework for this day is in [`day-29-ai-tools-foundations/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-29-ai-tools-foundations/homework.md) and is repeated at the bottom of this page.

## What is in the folder

47 files. Paths below are relative to the repo root unless noted.

### day-29-ai-tools-foundations/ai-devex/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/.gitignore` | Files git should not track for this folder. |  |
| `ai-devex/README.md` | Document: day-29-ai-tools-foundations/ai-devex |  |
| `ai-devex/requirements.txt` | Pinned Python dependencies for this folder. |  |

### day-29-ai-tools-foundations/ai-devex/decision/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/decision/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/decision/classify.py` | Turn Jev's per-question probabilities into one flaky probability and readable reasons. The weights are ours, a starting point to tune on labelled data. |  |
| `ai-devex/decision/dataset.jsonl` | Sample data file with fictional values. |  |
| `ai-devex/decision/evaluate.py` | Score a decision backend on the labelled dataset and show what thresholds buy you. |  |
| `ai-devex/decision/make_dataset.py` | Generate a SYNTHETIC labelled dataset of failing CI test runs: |  |

### day-29-ai-tools-foundations/ai-devex/evals/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/evals/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/evals/run_evals.py` | A deliberately small eval harness: tasks.json, deterministic checks (no LLM judge), N repeats, a per-model table. |  |
| `ai-devex/evals/tasks.json` | JSON data or configuration file. |  |

### day-29-ai-tools-foundations/ai-devex/gateway/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/gateway/ask.py` | Ask one or more models the same question through an OpenAI-compatible gateway and compare answer, latency and cost. |  |

### day-29-ai-tools-foundations/ai-devex/incident-to-pr/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/incident-to-pr/.gitignore` | Files git should not track for this folder. |  |
| `ai-devex/incident-to-pr/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/incident-to-pr/pipeline.py` | POST /api/v1/repos/&#123;owner&#125;/&#123;repo&#125;/pulls. The branch must already be pushed. Not run against a real Forgejo by the author; see tests (fake server). |  |
| `ai-devex/incident-to-pr/fixtures/alert.json` | JSON data or configuration file. |  |
| `ai-devex/incident-to-pr/fixtures/context.json` | JSON data or configuration file. |  |
| `ai-devex/incident-to-pr/sample-app/conftest.py` | Python module. |  |
| `ai-devex/incident-to-pr/sample-app/pricing.py` | Python module. Defines: `apply_discount`, `total`. |  |
| `ai-devex/incident-to-pr/sample-app/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `ai-devex/incident-to-pr/sample-app/tests/test_pricing.py` | Automated tests for pricing. |  |

### day-29-ai-tools-foundations/ai-devex/lib/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/lib/llm.py` | One tiny OpenAI-compatible chat client (stdlib only) so every lab talks to a gateway the same way. |  |

### day-29-ai-tools-foundations/ai-devex/metrics/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/metrics/001_ai_tables.sql` | Outcome metrics for AI-assisted work. One row per change (PR); one row per incident; one row per test per day. |  |
| `ai-devex/metrics/queries.sql` | name: lead_time_hours_by_author |  |

### day-29-ai-tools-foundations/ai-devex/sandbox/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/sandbox/bad-job.yaml` | Every classic mistake in one Job. check_job.py should flag all of them. Defines: Job. |  |
| `ai-devex/sandbox/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/sandbox/check_job.py` | Lint a Kubernetes manifest (Job + NetworkPolicy) for the properties an agent sandbox needs. |  |
| `ai-devex/sandbox/good-job.yaml` | A sandbox Job for an untrusted agent: no privileges, no host access, no cluster API token, no network except what the policy allows. Defines: Job, NetworkPolicy. |  |

### day-29-ai-tools-foundations/ai-devex/skills/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/skills/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/skills/check_skills.py` | CI guard rails for a skills registry: every skill is a folder with SKILL.md. |  |
| `ai-devex/skills/examples/bad-skill/SKILL.md` | name: Helper |  |
| `ai-devex/skills/examples/write-runbook/SKILL.md` | Document: Write a runbook |  |
| `ai-devex/skills/examples/write-runbook/templates/runbook.md` | Document: Runbook: &lt;alert&gt; |  |

### day-29-ai-tools-foundations/ai-devex/specs/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/specs/captured-output.txt` | Text file (sample data or captured output). |  |
| `ai-devex/specs/check_spec.py` | Lint a spec file so an agent never starts from a vague one. Exit 0 = ok, 1 = problems (printed one per line). Usage: check_spec.py SPEC.md [SPEC.md ...] Wire it into CI for any path under specs/ or docs/specs/. |  |
| `ai-devex/specs/spec-template.md` | Document: Problem |  |
| `ai-devex/specs/examples/bad.md` | Document: Problem |  |
| `ai-devex/specs/examples/good.md` | Document: Problem |  |

### day-29-ai-tools-foundations/ai-devex/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `ai-devex/tests/conftest.py` | Python module. Defines: `_H`, `fake_server`. |  |
| `ai-devex/tests/test_decision.py` | Automated tests for decision. |  |
| `ai-devex/tests/test_evals.py` | Automated tests for evals. |  |
| `ai-devex/tests/test_gateway.py` | Automated tests for gateway. |  |
| `ai-devex/tests/test_incident_to_pr.py` | Automated tests for incident to pr. |  |
| `ai-devex/tests/test_metrics_sql.py` | Every table and query in metrics/, run on embedded ClickHouse (chdb) with seeded rows. Skips without chdb. |  |
| `ai-devex/tests/test_sandbox.py` | Automated tests for sandbox. |  |
| `ai-devex/tests/test_skills.py` | Automated tests for skills. |  |
| `ai-devex/tests/test_specs.py` | Automated tests for specs. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-29-ai-tools-foundations/ai-devex
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests/test_metrics_sql.py -q
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
......                                                                   [100%]
6 passed in 0.25s
```

## How these files relate to other days and shared tools

- Builds on [Day 16](/days/day-16-secrets-management-openbao/), [Day 17](/days/day-17-observability/), [Day 25](/days/day-25-internal-platform/) (cluster, images or secrets created there).
- Files from this folder are used by [Day 30](/days/day-30-ai-agents-and-sandboxes/), [Day 31](/days/day-31-ai-quality-specs-evals-decisions/), [Day 32](/days/day-32-incident-to-reviewed-pr/).

## Homework

1. **Filter three tools.** Pick three AI tools your team has been asked about. Run each through the filter above on one page. Recommend: try, park or ignore, with a metric for each "try".
2. **Pick your metrics.** From the table, choose the five outcome measures you could actually collect in your company next quarter. For each, name the system that has the data and the person who owns it.
3. **Cost a workload.** Take a real task (for example "review every PR in one repo") and estimate the monthly cost at each tier with current prices, with and without caching. State assumptions. Mark which numbers you looked up and when.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Filter use** | Opinions | Each tool answered on the checklist | A decision with a baseline, an owner and an end date |
| **Metrics** | Token or usage counts | Outcome metrics named | Each has a data source, an owner, a gaming risk and a counter-measure |
| **Cost model** | One price, no assumptions | Tiers compared | Assumptions explicit, caching considered, dates on every price, sensitivity (what if usage doubles) |
| **Honesty** | Vendor claims repeated | Sources named | Distinguishes "I measured it" from "the vendor says" |
