# __APP__ architecture

## Context

What problem this solves and what it deliberately does not do.

## Components

```mermaid
flowchart LR
    U["Client"] --> I["Traefik ingress"]
    I --> A["__APP__ API"]
    A --> D[("Postgres")]
    A --> B[("Object storage")]
    A -. "metrics, logs" .-> O["OTel Collector"]
```

## Data

What is stored, where, how long, and who may read it.

## Failure modes

| Failure | Behaviour | Mitigation |
|---|---|---|
| Database down | `/readyz` fails; requests return 503 | retry with backoff; alert |

## Decisions

See [adr/](adr/).
