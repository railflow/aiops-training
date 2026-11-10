---
title: Why docs live in git
description: The reason docs go stale, and the loop that stops it.
---

Docs go stale for one reason: **nothing breaks when they do.** So we make something break.

```mermaid
flowchart LR
    A["Change code"] --> B["Change docs<br/>in the same PR"]
    B --> C["CI: docs gate"]
    C --> D["CI: build and link check"]
    D --> E["Review"]
    E --> F["Merge to main"]
    F --> G["Build image,<br/>Flux deploys it"]
```

Each box is a place a stale page can be caught. Start with the [overview](/start/overview/) and then try the [rollback guide](/how-to/roll-back-a-deploy/).
