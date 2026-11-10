---
title: "Day 34: Building an agent harness with Google ADK"
description: "Files in day-34-agent-harness-adk/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 34: Building an agent harness with Google ADK"
  order: 34
---

This page is the file-by-file guide to [`day-34-agent-harness-adk/`](https://github.com/railflow/aiops-training/tree/main/day-34-agent-harness-adk) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: One hundred repositories, one Kubernetes Job each, an agent in every Job. Write the harness yourself and meet every case it has to handle, then rewrite it with Google's Agent Development Kit and see exactly what the framework takes off your plate, and what it does not.

Homework for this day is in [`day-34-agent-harness-adk/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-34-agent-harness-adk/homework.md) and is repeated at the bottom of this page.

## What is in the folder

38 files. Paths below are relative to the repo root unless noted.

### day-34-agent-harness-adk/agent-harness-adk/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/.dockerignore` | Files kept out of the Docker build context. |  |
| `agent-harness-adk/.gitignore` | Files git should not track for this folder. |  |
| `agent-harness-adk/Dockerfile` | Build from the repository root (aiops-training): docker build -f day-34-agent-harness-adk/agent-harness-adk/Dockerfile -t agent-harness:dev . |  |
| `agent-harness-adk/README.md` | Document: Agent harness: hand-rolled vs Google ADK |  |
| `agent-harness-adk/requirements.txt` | Pinned Python dependencies for this folder. | `pip install -r requirements.txt` |
| `agent-harness-adk/run-on-kind.sh` | Run the fan-out on the course's kind cluster with the mock model. |  |

### day-34-agent-harness-adk/agent-harness-adk/adk/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/adk/__init__.py` | Python module. |  |
| `agent-harness-adk/adk/models.py` | Models for the ADK agents: an offline stub for the lab, Gemini or LiteLLM for the real thing. |  |
| `agent-harness-adk/adk/parallel_batch.py` | ParallelAgent: in-process concurrency for a handful of independent sub-tasks inside ONE Job. |  |
| `agent-harness-adk/adk/pipeline.py` | The same coverage agent, written with Google ADK. |  |
| `agent-harness-adk/adk/run_repo.py` | One Kubernetes Job = one repository, ADK edition. Same worker contract as hand_rolled/agent_loop.py: env in, `RESULT {json}` out, same exit codes. |  |
| `agent-harness-adk/adk/tools.py` | Tools as plain Python functions. ADK reads the signature and docstring and builds the schema the model sees. |  |
| `agent-harness-adk/adk/coverage_agent/__init__.py` | Python module. |  |
| `agent-harness-adk/adk/coverage_agent/agent.py` | Entry point for `adk run adk/coverage_agent` and `adk web adk`: the same pipeline, with state seeded from the environment. |  |

### day-34-agent-harness-adk/agent-harness-adk/common/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/common/__init__.py` | Python module. |  |
| `agent-harness-adk/common/approval.py` | A human gate before the irreversible step (opening a pull request). The policy is yours with or without a framework. |  |
| `agent-harness-adk/common/faults.py` | Failure injection for the lab. CHAOS="repo-a:stuck+bad_test,repo-b:oom@1,repo-c:rate_limit:3". |  |
| `agent-harness-adk/common/mock_llm.py` | A deterministic stand-in for a model. It is NOT a model. |  |
| `agent-harness-adk/common/repo_tools.py` | The tools the model gets, as plain functions. Both engines use exactly these, so the comparison is fair. |  |
| `agent-harness-adk/common/repos.py` | Repository specs and a way to materialise one offline. |  |
| `agent-harness-adk/common/settings.py` | Worker settings, read from the environment the Job sets. Shared by both engines. |  |

### day-34-agent-harness-adk/agent-harness-adk/fanout/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/fanout/__init__.py` | Python module. |  |
| `agent-harness-adk/fanout/orchestrator.py` | Fan-out / fan-in: one Kubernetes Job per repository, results collected into a ledger and a summary. |  |

### day-34-agent-harness-adk/agent-harness-adk/hand_rolled/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/hand_rolled/__init__.py` | Python module. |  |
| `agent-harness-adk/hand_rolled/agent_loop.py` | The hand-rolled per-repo agent: one Kubernetes Job runs this for one repository. |  |
| `agent-harness-adk/hand_rolled/llm.py` | The model client of the hand-rolled harness: a mock for the lab, an OpenAI-compatible HTTP client for the real thing. |  |
| `agent-harness-adk/hand_rolled/naive_loop.py` | The first version everyone writes: ask the model, run the tool it names, feed the result back, repeat until it stops asking. |  |
| `agent-harness-adk/hand_rolled/skeletons/AgentLoop.java` | Java source. Defines: `AgentLoop`, `Call`, `Reply`. |  |
| `agent-harness-adk/hand_rolled/skeletons/agent_loop.go` | The agent loop of one Job in Go. Same cases as agent_loop.py, minus JSON and HTTP plumbing (encoding/json and net/http cover both). Compile check: go vet ./... in this folder (needs a go.mod; see the README). |  |

### day-34-agent-harness-adk/agent-harness-adk/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/tests/conftest.py` | Python module. Defines: `spec`, `repo_dir`, `worker_env`, `run_worker`. |  |
| `agent-harness-adk/tests/fake_kubectl.py` | A stand-in for kubectl that runs each Job as a local subprocess. |  |
| `agent-harness-adk/tests/test_adk_units.py` | ADK behaviours the Day 34 page states, checked in isolation against the pinned version. |  |
| `agent-harness-adk/tests/test_concerns.py` | Automated tests for concerns. |  |
| `agent-harness-adk/tests/test_engines.py` | Both engines run as real worker processes (the way a Job runs them) against the mock model, with every fault the catalogue lists. |  |
| `agent-harness-adk/tests/test_naive_loop.py` | The first-draft loop on a good day and on each bad day. These tests document the failures Day 34 starts from. |  |
| `agent-harness-adk/tests/test_orchestrator.py` | The fan-out against a fake kubectl that runs each Job as a local process. Real workers, mock model, injected infrastructure faults. |  |
| `agent-harness-adk/tests/test_tools.py` | Automated tests for tools. |  |

### day-34-agent-harness-adk/agent-harness-adk/tools/

| File | What it is | How the lesson uses it |
|---|---|---|
| `agent-harness-adk/tools/count_concerns.py` | Count the lines of code each concern costs, per owner, from the `# >> Cnn name` / `# << Cnn` markers in the source. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-34-agent-harness-adk/agent-harness-adk
./run-on-kind.sh hand 12 6 --chaos 'billing-py-001:oom@1,booking-py-002:stuck,catalog-py-003:rate_limit:3,csv-importer-py-004:malformed_json+bad_test,inventory-py-005:crash@1'
```

```bash
cd day-34-agent-harness-adk/agent-harness-adk && PYTHONPATH=. python -m adk.parallel_batch 3
```

```bash
cd day-34-agent-harness-adk/agent-harness-adk
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests -q
```

```bash
git add day-34-agent-harness-adk/agent-harness-adk docs
git commit -m "Add my extra failure case and its handler to both harness engines"
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
{
  "run_id": "h1",
  "repos": 12,
  "finished": 12,
  "by_status": { "succeeded": 11, "stuck_loop": 1 },
  "retries": 2,
  "failed": [],
  "prs_opened": 11,
  "duplicate_prs": 0,
  "avg_coverage_before": 27.6,
  "avg_coverage_after": 80.7,
  "cost_usd": 0.7237
}
```

## How these files relate to other days and shared tools

- Builds on [Day 3](/days/day-03-kind-kubernetes/), [Day 5](/days/day-05-kubernetes-jobs/), [Day 27](/days/day-27-durable-workflows-temporal/), [Day 30](/days/day-30-ai-agents-and-sandboxes/) (cluster, images or secrets created there).
- Refers to files in [Capstone](/days/capstone/) (for example from `day-34-agent-harness-adk/agent-harness-adk/Dockerfile`).

## Homework

**Pick one and time-box it to a couple of hours:**

1. **A case the catalogue does not have.** Think of a failure this harness does not handle (a node drain during the PR step, a repository whose tests need a database, a model that returns plausible but wrong paths). Add it to `common/faults.py`, write a failing test, handle it in **both** engines, and add a `# >> C19` marker so the counter picks it up.
2. **Port the pipeline to a `Workflow`.** Use ADK 2.0's graph-based workflow instead of `SequentialAgent` and `LoopAgent`, give the nodes `retry_config` and timeouts, and keep the tests green. Report what got simpler and what the deprecation warning's note about `LlmAgent` sub-agents cost you.
3. **Take the state off the node.** Replace the `hostPath` volume and the SQLite session file with a PersistentVolumeClaim, or with a database session service (this needs the `db` extra). Show that a retry on a **different node** still resumes.
4. **The decision memo.** One page: for the capstone's agent fleet, would you use a hand-rolled loop, ADK, ADK inside Temporal activities, or something else? Use the "what it took over" table as evidence and name what would change your mind.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Cases** | Names two or three | Maps each failure to a handler and a test | Finds a case not in the table and shows it injected and survived |
| **Honesty** | "ADK handles it" | Separates plumbing from policy | Tests the claim against the pinned version instead of the docs alone |
| **Resume** | Restarts from zero | Resumes state | Resumes state **and** the working tree, and says what is lost |
| **Cost** | No numbers | Counts tokens or lines | Compares engines on the same run, and says what the mock hides |
| **Evidence** | Claims only | A test or captured run | Tests plus a failure injected on purpose |

### Ask AI (use it as a reviewer, not an author)

- "Here is my agent loop. List every way it can run forever, spend unbounded money, or report success without doing the work."
- "Here is my Job manifest. What happens when the node is drained, the pod is OOM-killed, or the orchestrator restarts?"
- "Argue the case **against** adding an agent framework to this. What is the cheaper alternative?"
- "Given this ADK pipeline, which behaviour would change if I upgraded from 2.13.0 to the next minor version, and how would I find out before production?"

Check anything it says about ADK against [adk.dev](https://adk.dev/) and, better, against a test on your pinned version.
