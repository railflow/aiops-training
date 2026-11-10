# __APP__

One sentence: what this service does and for whom.

| | |
|---|---|
| Owner | team-name (channel: #team-channel) |
| Status | experimental / production |
| URL | http://__APP__.localhost:8080 |
| Runbook | [docs/runbook.md](docs/runbook.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Decisions | [docs/adr/](docs/adr/) |

## Run it locally

```bash
# the exact commands that work today, copy-pasteable
```

## Test it

```bash
build.sh build test secure docs
```

## Configuration

| Variable | Meaning | Default | Where the real value comes from |
|---|---|---|---|
| `PORT` | HTTP port | `8080` | - |

Never put a secret value in this table or anywhere in this repository.
