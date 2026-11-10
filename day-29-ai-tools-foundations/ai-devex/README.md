# day-29-ai-tools-foundations/ai-devex

Code for **Days 29-32** (AI tools in DevEx). Everything has an offline mode and tests; nothing here needs an API key to run the tests.

| Folder | What it is | Verified by running |
|---|---|---|
| `lib/llm.py`, `gateway/ask.py` | A tiny OpenAI-compatible client and a "ask N models the same question" script | Request shape and parsing against a **local fake server**. Never against a real gateway. |
| `specs/` | Spec template, `check_spec.py` CI lint, a good and a bad example | Yes (tests + captured output) |
| `evals/` | 5-task harness with deterministic checks, offline mock models, gateway mode | Offline yes; gateway mode against a fake server only |
| `decision/` | Synthetic flaky-test dataset, heuristic and Jev backends, thresholds, review band, precision/recall | Heuristic yes. Jev backend: request/response shape against a fake server only (the Decisions API is alpha) |
| `metrics/` | ClickHouse tables and outcome-metric queries | Yes, on embedded ClickHouse (chdb) with seeded rows |
| `sandbox/` | `check_job.py`: lints a Job + NetworkPolicy for agent-sandbox properties; a good and a bad manifest | Yes (tests + captured output). Nothing was applied to a cluster |
| `skills/` | `check_skills.py`: registry CI guard rails and a prune-candidate report; a good and a bad skill | Yes |
| `incident-to-pr/` | The day-32 pipeline: alert, context, triage, fix agent, measure, PR, separate reviewer, human gate | Offline end to end with a real `measure.py` + pytest-cov run. Real models and real Forgejo: shape only (fake servers) |

## Run the tests

```bash
python3 -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests -q
```

Last run: 46 tests passed (Python 3.12, chdb and pytest-cov installed).

## What is NOT verified here

- Any real model, any real OpenRouter call, any real Jev call, any real Forgejo PR.
- Kubernetes Jobs or Temporal for the incident pipeline (the page explains the mapping; the code is a plain script).
- The numbers in the datasets are synthetic. The precision and recall you see describe the toy heuristic on made-up data, not a model.

Keys come from the environment only (`OPENROUTER_API_KEY`), from OpenBao in the course setup. Never commit one.
