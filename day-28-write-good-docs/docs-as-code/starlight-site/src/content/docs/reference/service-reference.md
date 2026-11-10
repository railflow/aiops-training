---
title: Service reference
description: Endpoints and settings, in a table.
---

## Endpoints

| Path | Method | Meaning |
|---|---|---|
| `/healthz` | GET | Returns `200 ok` when the process is up |
| `/orders` | GET | Lists orders |
| `/orders/{id}` | GET | One order, or `404` |

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | Listen port (non-root processes cannot bind 80) |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn` or `error` |
| `DATABASE_URL` | none | Connection string, injected from a Secret |

See [Roll back a deploy](/how-to/roll-back-a-deploy/) for what to do when a release breaks these.
