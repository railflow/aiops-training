> Files for the Capstone of the AI Ops Academy course. Homework: [`homework.md`](homework.md). File-by-file guide: run `./build.sh` in the repository root, then open `http://localhost:4321/days/capstone/`.

# Capstone: the AI agent army (reference scaffolding)

This folder is the **instructor's reference kit** for the capstone homework (the Capstone lesson on the course site). Learners are meant to build their own version; this
exists so every piece can be exercised end to end on 3-5 tiny repos before scaling to 100+.

| Folder | What it is | Tested how |
|---|---|---|
| `sql/` | ClickHouse tables (`capstone.*`) and the named queries | run against embedded ClickHouse (chdb) |
| `gen/` | deterministic repo generator + planted bugs + answer keys, AI-generation prompt | built and tested: python, node, java. go/dotnet generated only |
| `measure/` | `measure.py`, `ship.py`, baseline Indexed Job, measure image | parsers on fixtures, python/node/java for real |
| `forgejo/` | `push_repos.py/.sh`, `cleanup.sh`, golden-path `ci.yaml` | against a fake Forgejo API; **not** a real Forgejo |
| `webhook/` | FastAPI receiver, HMAC verification, routing | FastAPI test client; not from a real Forgejo delivery |
| `agent/` | agent Job entrypoint, evaluate Job, integrity check, issue filer, prompts, Job templates | with a stub `claude` and `file://` remotes; **no real model run** |
| `workflows/` | Temporal workflows, activities, JobRunner, worker, `start.py` | time-skipping test server with fake activities |
| `k8s/` | namespace, quota, priority, NetworkPolicy, RBAC, worker Deployment | YAML parsed only, **not applied** (no cluster here) |
| `dashboards/` | Grafana JSON generator (portfolio, drilldown) | SQL run in chdb; JSON never opened in Grafana |
| `tests/` | all of the above | `pip install -r measure/requirements.txt temporalio fastapi httpx pyyaml pytest-asyncio` then `pytest tests` |

Start with `gen/make-samples.sh`, then `measure/measure.py`, then read the page.

**Safety:** nothing here is meant to run against a repo or cluster you care about. The agent Jobs spend real money when pointed at a real model.
