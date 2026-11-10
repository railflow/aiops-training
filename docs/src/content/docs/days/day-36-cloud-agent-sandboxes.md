---
title: "Day 36: Cloud agent sandboxes"
description: "Files in day-36-cloud-agent-sandboxes/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 36: Cloud agent sandboxes"
  order: 36
---

This page is the file-by-file guide to [`day-36-cloud-agent-sandboxes/`](https://github.com/railflow/aiops-training/tree/main/day-36-cloud-agent-sandboxes) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Why an agent that runs code needs a boundary, in a company and on your own laptop. Run one task on an offline mock, then map it onto Vercel Sandbox, Modal Sandboxes and Daytona, and compare them cell by cell with every cell labelled as read from the docs or my assessment.

Homework for this day is in [`day-36-cloud-agent-sandboxes/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-36-cloud-agent-sandboxes/homework.md) and is repeated at the bottom of this page.

## What is in the folder

46 files. Paths below are relative to the repo root unless noted.

### day-36-cloud-agent-sandboxes/agent-sandboxes/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/.env.example` | Template of the environment variable names this folder reads; copy to .env and fill in your own values. Contains no real values. |  |
| `agent-sandboxes/.gitignore` | Files git should not track for this folder. |  |
| `agent-sandboxes/README.md` | Document: Cloud agent sandboxes (Day 36) |  |
| `agent-sandboxes/pytest.ini` | pytest settings for this folder. |  |
| `agent-sandboxes/requirements-offline.txt` | Pinned Python dependencies for this folder. | `pip install -r requirements-offline.txt` |
| `agent-sandboxes/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `agent-sandboxes/run_mock.py` | The default path: run the common task on the offline mock provider. No network, no account, no cost. | `python run_mock.py` |

### day-36-cloud-agent-sandboxes/agent-sandboxes/common/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/common/__init__.py` | Python module. |  |
| `agent-sandboxes/common/fake_agent.py` | A scripted stand-in for the model. It is NOT a model: it looks at which functions have no coverage and writes tests from a table. |  |
| `agent-sandboxes/common/provider.py` | The whole provider interface: create, exec, upload, download, destroy (plus an optional native checkout). |  |
| `agent-sandboxes/common/real.py` | Load a real provider by file path. |  |
| `agent-sandboxes/common/run_task.py` | One task, any provider: checkout, upload tools, install, baseline coverage, agent writes a test, verify, collect the diff. |  |
| `agent-sandboxes/common/spec.py` | The vocabulary shared by every provider. Nothing here can hold a secret value, only names. |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/daytona/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/daytona/provider.py` | Daytona Sandboxes behind the shared provider interface. |  |
| `agent-sandboxes/daytona/run_task.py` | Run the common task on Daytona. From day-36-cloud-agent-sandboxes/agent-sandboxes: python daytona/run_task.py |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/lab/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/lab/__init__.py` | Python module. |  |
| `agent-sandboxes/lab/captured-output.txt` | Text file (sample data or captured output). |  |
| `agent-sandboxes/lab/captured-run-mock-injected.json` | JSON data or configuration file. |  |
| `agent-sandboxes/lab/captured-run-mock.json` | JSON data or configuration file. |  |
| `agent-sandboxes/lab/scenarios.py` | The 'what could go wrong' lab: commands a prompt-injected agent might run, and what each one reaches. |  |
| `agent-sandboxes/lab/what_could_go_wrong.py` | python lab/what_could_go_wrong.py : run each hostile command on a bare machine and in a sandbox, in the offline mock. |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/mock/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/mock/__init__.py` | Python module. |  |
| `agent-sandboxes/mock/provider.py` | An offline provider. Benign commands of the task really run in a temporary directory; every other command is only *modelled*. |  |
| `agent-sandboxes/mock/threats.py` | How the mock understands a command. It is a MODEL of what dangerous commands do, written for teaching. |  |
| `agent-sandboxes/mock/world.py` | The two worlds a command can land in: a bare machine, or a sandbox with the properties the providers document. |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/modal/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/modal/provider.py` | Modal Sandboxes behind the shared provider interface. |  |
| `agent-sandboxes/modal/run_task.py` | Run the common task on Modal. From day-36-cloud-agent-sandboxes/agent-sandboxes: python modal/run_task.py |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/task/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/task/task.json` | JSON data or configuration file. |  |
| `agent-sandboxes/task/expected/test_generated_stock.py` | Generated by the scripted agent. Functions covered: remove_item, low_stock, total_value, restock_plan. |  |
| `agent-sandboxes/task/sample-repo/README.md` | Document: inventory |  |
| `agent-sandboxes/task/sample-repo/requirements.txt` | Pinned Python dependencies for this folder. |  |
| `agent-sandboxes/task/sample-repo/src/inventory/__init__.py` | Python module. |  |
| `agent-sandboxes/task/sample-repo/src/inventory/stock.py` | A small inventory library. The tests cover only part of it, which is the point of the exercise. |  |
| `agent-sandboxes/task/sample-repo/tests/test_stock.py` | Automated tests for stock. |  |
| `agent-sandboxes/task/tools/cov.py` | Line coverage with the standard library only, so the lab runs anywhere with Python 3.10 or newer. |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/tests/conftest.py` | Python module. |  |
| `agent-sandboxes/tests/test_providers_offline.py` | The Modal and Daytona providers, driven by hand-written fakes that mimic the SDK shapes. Proves the mapping and the call sequence, not that the real services behave this way (they were not reachable; see README). |  |
| `agent-sandboxes/tests/test_sdk_surface.py` | Every SDK name the real runners use must exist in the pinned SDK versions. Skipped when the SDK is not installed. |  |
| `agent-sandboxes/tests/test_task_on_mock.py` | Automated tests for task on mock. |  |
| `agent-sandboxes/tests/test_threat_lab.py` | Automated tests for threat lab. |  |

### day-36-cloud-agent-sandboxes/agent-sandboxes/vercel/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-sandboxes/vercel/package-lock.json` | Dependency lockfile generated by the package manager; do not edit by hand. |  |
| `agent-sandboxes/vercel/package.json` | Node project manifest for agent-sandboxes-vercel. Scripts: typecheck, test, run:real. |  |
| `agent-sandboxes/vercel/provider.ts` | Provider interface (the TypeScript twin of common/provider.py) and the Vercel Sandbox implementation. Verified against @vercel/sandbox 3.9.1 types; NOT run against a live account (see README). |  |
| `agent-sandboxes/vercel/run-task.ts` | The same task as common/run_task.py, written against the TypeScript Provider interface. | `SANDBOX_ALLOW_REAL=1 node run-task.ts` (real: needs VERCEL_OIDC_TOKEN (or the team, project and token trio)) |
| `agent-sandboxes/vercel/tsconfig.json` | TypeScript compiler settings. |  |
| `agent-sandboxes/vercel/test/run-task.test.ts` | Automated tests for run task. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-36-cloud-agent-sandboxes/agent-sandboxes
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-offline.txt
pytest -q
python run_mock.py
```

```bash
cd day-36-cloud-agent-sandboxes/agent-sandboxes/vercel
npm install && npm run typecheck && npm test      # offline: 4 tests against a fake provider
SANDBOX_ALLOW_REAL=1 node run-task.ts             # real: needs VERCEL_OIDC_TOKEN (or the team, project and token trio)
```

```bash
cd day-36-cloud-agent-sandboxes/agent-sandboxes
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-offline.txt
pytest -q                 # 38 pass, 2 skip (the SDK-surface checks need modal and daytona installed)
```

```bash
git add day-36-cloud-agent-sandboxes/agent-sandboxes docs
git commit -m "Add an eleventh hostile scenario to the sandbox threat lab"
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
"provider": "mock-sandbox",
"coverage_before": 55.2,
"coverage_after": 100.0,
"steps": create, checkout, upload_tools, install, baseline, agent, verify, collect, destroy
diff: diff --git a/tests/test_generated_stock.py b/tests/test_generated_stock.py  (new file, 27 lines)
```

## How these files relate to other days and shared tools

- Builds on [Day 30](/days/day-30-ai-agents-and-sandboxes/), [Day 34](/days/day-34-agent-harness-adk/), [Day 35](/days/day-35-durable-agents-eve/) (cluster, images or secrets created there).

## Homework

Pick one:

1. **A fourth adapter.** Write an adapter for E2B or Cloudflare behind the same interface, with a fake-SDK test like `tests/test_providers_offline.py`. Mark every API name you cannot verify against the package.
2. **A new hostile scenario.** Add an eleventh scenario to `lab/scenarios.py` (for example, a symlink to `/etc/passwd`, a DNS-based exfiltration, or a write to a mounted volume). Show what the bare world and the sandbox do, and say honestly where the mock is too simple to tell.
3. **A real run and a real number.** Run the task on one provider and report cold start (`create` to first `exec`), total time, and cost against the list-price arithmetic. Do not commit credentials or full logs.
4. **A policy.** Write the Day 36 decision for your own team: which workloads need which boundary, which tokens, which TTL, and what approval, in half a page.

### How you will be graded

| | Basic | Good | Excellent |
|---|---|---|---|
| **Threat model** | Lists threats | Maps each to what a sandbox gives | Also says what it does not solve, with a test |
| **Claims** | "Provider X is secure" | Each claim has a source | Separates docs, mock and assessment, as the page does |
| **Secrets** | Environment variables | Placeholders or brokering | Explains where the value lives for each provider and the blast radius if the agent is injected |
| **Cost** | Ignores it | Sets a TTL | Computes the cost of the timeout and compares it with a real bill |
| **Honesty** | Hides what was not run | Lists it | Lists it and says how to test it |

### Ask AI (use it as a reviewer, not an author)

- "Here is my sandbox spec. List what an injected agent could still reach, and what I would have to change to stop each one."
- "My allow-list includes `github.com`. How can an attacker still use that, and what limits it?"
- "Argue for and against running this on a hardened Kubernetes Job instead of a hosted sandbox. What would make you switch?"
- "Which of the claims in my comparison table could be checked with a script against a live account? Write the script."

Check anything it says about a provider against that provider's current documentation. These products change monthly; an answer from memory may describe a version that no longer exists.
