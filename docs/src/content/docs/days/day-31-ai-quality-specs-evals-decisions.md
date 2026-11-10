---
title: "Day 31: Quality: specs, evals and decision models"
description: "Files in day-31-ai-quality-specs-evals-decisions/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 31: Quality: specs, evals and decision models"
  order: 31
---

This page is the file-by-file guide to [`day-31-ai-quality-specs-evals-decisions/`](https://github.com/railflow/aiops-training/tree/main/day-31-ai-quality-specs-evals-decisions) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Write specs an agent can follow and CI can check, choose between reasoning and code models, measure with evals instead of vibes, and use decision models for judgement calls with thresholds and a human-review band.

Homework for this day is in [`day-31-ai-quality-specs-evals-decisions/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-31-ai-quality-specs-evals-decisions/homework.md) and is repeated at the bottom of this page.

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
python3 specs/check_spec.py specs/examples/good.md specs/examples/bad.md
```

```bash
cd day-29-ai-tools-foundations/ai-devex
python3 evals/run_evals.py --model mock:careful --model mock:sloppy
```

```bash
cd day-29-ai-tools-foundations/ai-devex
head -2 decision/dataset.jsonl
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
specs/examples/good.md: ok
specs/examples/bad.md: section 'Non-goals' is missing or empty
specs/examples/bad.md: section 'Rollback' is missing or empty
specs/examples/bad.md: AC-1: vague word 'well'; say what is measured
specs/examples/bad.md: AC-2: vague word 'Clean'; say what is measured
specs/examples/bad.md: AC-2: too short to be checkable
specs/examples/bad.md: test plan: no mention of AC-1
specs/examples/bad.md: test plan: no mention of AC-2
```

```text
model                             pass   rate   avg s       cost  cost/pass
mock:careful                    5/5      100%    0.00    0.00000    0.00000
mock:sloppy                     0/5        0%    0.00    0.00000        n/a
  FAIL mock:sloppy extract-version
  FAIL mock:sloppy classify-log-severity
  FAIL mock:sloppy fix-off-by-one
  FAIL mock:sloppy do-not-leak-secret
  FAIL mock:sloppy commit-message-format
```

## How these files relate to other days and shared tools

- Builds on [Day 9](/days/day-09-build-tools-and-tests/), [Day 28](/days/day-28-write-good-docs/), [Day 29](/days/day-29-ai-tools-foundations/), [Day 30](/days/day-30-ai-agents-and-sandboxes/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 29](/days/day-29-ai-tools-foundations/).

## Homework

1. **A real spec.** Write a spec for a real change in your team's repo and have an agent implement it. Record: how many times you had to correct it, which criteria it missed, and whether the checker would have flagged a weakness earlier.
2. **A real eval.** Build ten tasks from your own incident or PR history with deterministic checks. Run two models three times each. Report pass rate and cost per pass, and say what you would change in how you assign tasks to tiers.
3. **A real decision.** Pick one yes/no judgement your team makes repeatedly. Label 100 historical cases. Run a decision backend, choose `hi` and `lo` from the data, and report precision, recall and the human-review share. State what a wrong automatic decision costs.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Spec** | Prose wish | All sections, checker passes | Acceptance criteria map to named tests; non-goals prevented a real scope creep |
| **Eval design** | Tasks invented for the demo | Tasks from real work with deterministic checks | Held-out set, repeats, cost per pass, version and date recorded |
| **Decision policy** | One threshold chosen by feel | Thresholds chosen from a sweep | Review band sized against stated costs of each error; plan to feed human labels back |
| **Honesty** | Claims "AI works" | Reports numbers | Reports uncertainty, sample sizes, and what was not measured |
