# __APP__

One-line description: **replace me** (what it does and for whom).

| | |
|---|---|
| Owner | **replace me** (team or person, how to reach them) |
| URL | http://__APP__.localhost:8080 |
| Health | `/healthz` (process up), `/readyz` (can serve), `/version` (what is running) |
| Runbook | [docs/runbook.md](docs/runbook.md) |
| Deployed by | Flux, from the config repo (`apps/__APP__/`) |

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt pytest
pytest -q
python app.py                                            # http://localhost:8080
```

## Build and deploy

```bash
docker build -t localhost:30500/__APP__:0.1.0 --build-arg APP_VERSION=0.1.0 .
docker push localhost:30500/__APP__:0.1.0
kubectl apply -f k8s/            # first time only; afterwards, change the tag in the config repo
```

## What the platform gave you

- A pipeline (`.forgejo/workflows/ci.yaml`): test, build.
- A hardened Deployment (non-root, read-only filesystem, probes, limits).
- An address (`__APP__.localhost`) through Traefik.
- A default-deny NetworkPolicy with one allow rule (enforced only on a CNI that supports it).
- A health check entry for Gatus (`gatus-endpoint.yaml`).
- Optional shared database and bucket (`platform db __APP__`, `platform bucket __APP__`).
