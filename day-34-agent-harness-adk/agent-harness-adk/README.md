# Agent harness: hand-rolled vs Google ADK

The code behind Day 34 of the course. One job, written twice:
**raise the test coverage of 100+ repositories, one Kubernetes Job per repository, and open a pull request for each.**
Everything runs offline with a scripted stand-in for the model (`common/mock_llm.py`). It is a rule-based policy, **not a model**: the harness around it is real.

```
common/       tools and fixtures shared by both engines (pytest+coverage runner, safe file writer, git, a file-based fake forge, the mock model, fault injection)
hand_rolled/  the agent loop you write yourself: agent_loop.py (Python), skeletons/ (Java compiled with javac 22, Go vetted with golang:1.23)
adk/          the same agent with google-adk: tools.py, pipeline.py (SequentialAgent + LoopAgent), run_repo.py (Runner, sessions, resume), models.py
              parallel_batch.py (ParallelAgent demo), coverage_agent/ (entry point for `adk run` / `adk web`, not exercised)
fanout/       orchestrator.py: one Job per repo, concurrency cap, retries, ledger, fan-in. Needs only kubectl and the standard library
tests/        pytest suite; a fake kubectl runs each Job as a local process
tools/        count_concerns.py: counts the lines each failure case costs, from the `# >> Cnn` markers in the source
```

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m pytest tests -q                       # about 4 minutes; 75 tests, real worker processes, fake kubectl
python tools/count_concerns.py                  # the table in the Day 34 page

# one worker, the way a Job runs it (it materialises a repo from a seed)
export REPO_NAME=billing-py-001 WORK_DIR=/tmp/ah/work STATE_DIR=/tmp/ah/state FORGE_DIR=/tmp/ah/forge
PYTHONPATH=. python -m hand_rolled.agent_loop   # or: python -m adk.run_repo
```

On the course's kind cluster (own namespace `agent-harness`, refuses any other kubectl context):

```bash
./run-on-kind.sh adk 100 20 --budget-usd 40     # engine, repos, concurrency, then orchestrator flags
./run-on-kind.sh hand 12 6 --chaos 'billing-py-001:oom@1,booking-py-002:stuck'
./run-on-kind.sh clean
```

`--chaos` injects failures per repo: `stuck`, `bad_test`, `bad_tool`, `malformed_json`, `malformed_args`, `rate_limit:N`, `oom@K`, `crash@K`, `hang`, `die_at_test@K`. See `common/faults.py`.

## Worker contract (both engines)

Env in: `REPO_NAME REPO_DOMAIN REPO_SEED TARGET_COVERAGE MAX_STEPS BUDGET_USD STEP_TIMEOUT_S JOB_DEADLINE_S CONTEXT_TOKENS STATE_DIR WORK_DIR FORGE_DIR APPROVAL CHAOS LLM_MODE LLM_MODEL ATTEMPT RUN_ID`.
Out: logs as JSON on stderr, one `RESULT {json}` line on stdout. Exit codes: `0` finished (see `status`), `75` retry later (model unavailable), `143` cancelled, `137` killed (OOM), `1` crash.

## Measured here (mock model, kind v0.27 cluster, Apple silicon, Nov 2026)

| Run | Result |
|---|---|
| ADK, 100 repos, concurrency 20, chaos on 7 repos | 86 s; 97 succeeded, 2 `no_progress` (injected "stuck model"), 1 failed after 3 crashes; 5 retries; 97 PRs, 0 duplicates; coverage 27.7% to 83.4% |
| Hand-rolled, 12 repos, concurrency 6, chaos on 5 repos | 11 succeeded, 1 `stuck_loop`; 2 retries; 11 PRs; coverage 27.6% to 80.7% |
| ADK, same 12 repos and chaos | 11 succeeded, 1 `no_progress`; 2 retries; 11 PRs; coverage 27.6% to 80.7% |

The mock "dollars" are made up (`PRICE_PER_1K_TOKENS`); the ADK run reads more tokens per repo because three agents each re-read the conversation. Treat the ratio as an observation about this mock, not about real models.

## Not tested

A real model (Gemini, LiteLLM or an OpenAI-compatible endpoint), `adk run`, `adk web`, `adk eval`, `adk deploy`, Agent Runtime, GKE or Cloud Run, a real Forgejo for the PRs (the lab uses `FileForge`), a Postgres-backed session service, and the Go skeleton beyond `go vet` and a run of its stub.
