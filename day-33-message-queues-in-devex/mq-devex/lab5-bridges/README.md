# Lab 5 (optional): webhooks onto the bus

`bridge.py` is a small FastAPI app. Three routes, three vendors, one envelope:

| Route | Auth | Becomes |
| --- | --- | --- |
| `POST /forgejo` | HMAC-SHA256 of the raw body (same logic as the capstone webhook) | `scm.push`, `scm.pull_request`, `scm.issue` |
| `POST /keep` | `Authorization: Bearer $BRIDGE_TOKEN` | `alerts.keep.firing` / `alerts.keep.resolved` |
| `POST /gatus` | `Authorization: Bearer $BRIDGE_TOKEN` | `alerts.gatus.triggered` / `alerts.gatus.resolved` |

The event id comes from the delivery id, so a webhook the sender retries is dropped by the stream's duplicate window. Tested, including through a real NATS server (`tests/test_bridges.py`).

## Run

```bash
pip install fastapi uvicorn nats-py pyyaml
export NATS_URL=nats://127.0.0.1:4222 BRIDGE_FORGEJO_SECRET="$(openssl rand -hex 16)" BRIDGE_TOKEN="$(openssl rand -hex 16)"
python3 serve.py
# in another terminal: nats sub 'scm.>' ; nats sub 'alerts.>'
```

On kind: `PIP="nats-py==2.16.0 pyyaml fastapi uvicorn" ../k8s/deploy-worker.sh bridge lab5-bridges/serve.py`, put the two secrets in a Secret and mount them as env (not run here), and add a Service.

## Point the tools at it

Gatus, in `alerting.custom` (placeholders are from Gatus's README; this config was not run through Gatus):

```yaml
alerting:
  custom:
    url: "http://bridge.mq-devex.svc.cluster.local:8080/gatus"
    method: "POST"
    headers:
      Authorization: "Bearer ${BRIDGE_TOKEN}"
      Content-Type: "application/json"
    body: |
      {"state": "[ALERT_TRIGGERED_OR_RESOLVED]", "group": "[ENDPOINT_GROUP]", "name": "[ENDPOINT_NAME]",
       "description": "[ALERT_DESCRIPTION]", "errors": "[RESULT_ERRORS]"}
```

Forgejo: repo Settings -> Webhooks -> add a Forgejo (or Gitea) webhook to `http://<bridge>/forgejo` with the secret. Check "Recent Deliveries" for the header and event names your version sends.
Keep: a workflow with a webhook action pointing at `/keep`; the payload shape is an ASSUMPTION (see the docstring in `bridge.py`), so look at a real delivery and adjust `map_keep`.

## The capstone on the bus

The capstone's webhook receiver starts Temporal workflows directly. With the bridge, you can instead run a tiny consumer on `scm.push` that starts the same
`MeasureRepoWorkflow` (same deterministic workflow id), so the bus holds the history of what triggered what. That consumer is the homework extension in the course page; it is not built here.
