# Durable agents with Eve (Day 35)

The Day 34 coverage-improver agent, killed with `kill -9` in the middle of its work, in four implementations:

| Folder | What it is | Needs |
|---|---|---|
| `plain/` | A hand-rolled loop with no durability. The "before" picture. | Node 24 |
| `eve-app/` | The same agent as a real [Eve](https://vercel.com/eve) app (`eve@1.0.0-rc.5`), run offline with a scripted model. | Node 24 |
| `temporal/` | The same agent as a Temporal workflow (Python SDK) with a signal for approval. | Python 3.12, Temporal CLI |
| `adk/` | The same agent as a Google ADK app with a SQLite session and `require_confirmation`. | Python 3.12 |

There is no real model, no real git forge and no Vercel account involved. A scripted model (`eve-app/agent/lib/scripted-model.ts`, mirrored by `py/lab_common.py`) makes the same decisions every run, and the "forge" is a JSON file (`$LAB_DIR/forge.json`). Every tool appends to `$LAB_DIR/ledger.jsonl`, which is how the labs count how often each step ran and in which process.

## Run it

Eve needs Node 24 or newer (its `engines` field says `>=24`).

```bash
cd day-35-durable-agents-eve/durable-agents-eve
npm run install:eve && npm run build      # installs eve@1.0.0-rc.5 and compiles the app
npm test                                  # 10 node:test tests, no network
npm run lab                               # the six Eve scenarios and the two plain-loop scenarios, with assertions
```

Temporal (needs the Temporal CLI 1.10.0 on `PATH`, or `TEMPORAL_CLI=/path/to/temporal`):

```bash
python -m venv .venv-temporal && . .venv-temporal/bin/activate
pip install -r temporal/requirements.txt
cd temporal && pytest -q && python crash_lab.py
```

ADK:

```bash
python -m venv .venv-adk && . .venv-adk/bin/activate
pip install -r adk/requirements.txt
cd adk && pytest -q && python crash_lab.py
```

`lab/captured-output*.txt` hold the output of the runs that the Day 35 page quotes.

## Knobs (environment variables)

| Variable | Effect |
|---|---|
| `LAB_DIR` | Where the ledger, forge and state live. Each lab uses a fresh temp directory. |
| `LAB_STEP_MS` | How long each fake step takes. |
| `LAB_DIE_AT=tool:before\|after` | The process kills itself (exit 137, like `kill -9`) before or after a tool's side effect. |
| `LAB_NO_IDEMPOTENCY=1` | Make `open_pr` naive (no stable key) to show a duplicate pull request after a crash. |

## What these labs cannot tell you

Nothing here ran on Vercel: not Vercel Workflow, not Vercel Sandbox, not Agent Runs, not `eve deploy`. The Postgres world, real models, Slack and GitHub channels, schedules firing, subagent fan-out through `ctx.agent`, evals and the dev TUI were not exercised. The scripted model repeats an interrupted call by design; a real model may check first. See the Day 35 page for the full honesty note.
