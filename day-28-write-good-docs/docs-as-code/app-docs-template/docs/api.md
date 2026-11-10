# __APP__ API

Stub: replace with generated reference where you can (OpenAPI served at `/openapi.json`, `go doc`, Javadoc, Sphinx autodoc), and keep this page for what generators cannot say: authentication, pagination, errors, rate limits, examples.

## Authentication

How a client proves who it is (never include a real token in an example).

## Endpoints

| Method and path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /healthz` | liveness | `200 ok` | - |
| `GET /readyz` | readiness | `200 ready` | `503` when a dependency is down |

## Example

```bash
curl -s http://__APP__.localhost:8080/healthz
```
