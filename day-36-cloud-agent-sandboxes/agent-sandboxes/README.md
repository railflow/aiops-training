# Cloud agent sandboxes (Day 36)

One task, three providers, one offline mock. The task: clone a repository, install its dependencies, run its tests, let an agent write one test file, and return the diff and the coverage.

| Folder | What it is | Needs |
|---|---|---|
| `task/` | The shared task spec (`task.json`), a small sample repo with a prompt-injection line planted in its README, and a stdlib-only coverage tool. | nothing |
| `common/` | The provider interface (`create / exec / upload / download / destroy`), the task runner and a scripted stand-in for an agent. | Python 3.12 |
| `mock/` | An offline provider. Safe commands really run in a temp directory; dangerous ones are **modelled, never executed**. | Python 3.12 |
| `lab/` | "What could go wrong": ten malicious-looking tasks, with and without a sandbox. | Python 3.12 |
| `vercel/` | `@vercel/sandbox@3.9.1` runner and provider in TypeScript. | Node 24 |
| `modal/` | `modal==1.6.3` provider (`modal.Sandbox`). | Python 3.12 |
| `daytona/` | `daytona==0.230.0` provider. | Python 3.12 |

## Run it offline (the default path, no account, no network, no cost)

```bash
cd day-36-cloud-agent-sandboxes/agent-sandboxes
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-offline.txt
pytest -q                          # mock suite, threat lab, provider mappings (SDK checks skip without the SDKs)
python run_mock.py                 # the common task on the mock sandbox
python run_mock.py --injected      # the agent obeys the planted README line; the sandbox contains it
python run_mock.py --injected --bare   # the same agent on a bare-host model, for contrast
python lab/what_could_go_wrong.py  # ten hostile tasks, bare vs sandbox vs verdict
```

TypeScript (Node 24 or newer, for built-in type stripping):

```bash
cd vercel && npm install && npm run typecheck && npm test
```

`lab/captured-*` hold the output the Day 36 page quotes.

## Run it for real (optional, costs money, needs your own account)

Nothing in this folder was run against a live provider when it was written. Treat the first real run as a test of the runner, not of the docs.

1. Copy `.env.example` and set the variable **names** it lists for the provider you use. Never commit values.
2. `export SANDBOX_ALLOW_REAL=1`. The runners refuse to start without it, so credentials that happen to be in your environment or profile are not used by accident.
3. Run:

```bash
pip install -r requirements.txt    # adds modal and daytona
python modal/run_task.py
python daytona/run_task.py
cd vercel && npm install && node run-task.ts
```

Network policy for every real run comes from `task/task.json` (an allow-list of `pypi.org`, `files.pythonhosted.org` and `github.com`). On Daytona, Tier 1 and 2 organisations have org-level network limits that a per-sandbox list cannot override; on Vercel, header injection (`transform`) needs Pro or Enterprise. The Day 36 page has the details.

## What this cannot tell you

The mock is a model of what the providers document. It proves that the runner logic, the spec mapping and the cleanup path work; it proves nothing about how well any provider isolates anything. The scripted agent is not a model. See the Day 36 page for the full honesty note.
