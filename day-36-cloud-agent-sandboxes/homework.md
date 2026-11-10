# Day 36: Cloud agent sandboxes: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Pick one:

1. **A fourth adapter.** Write an adapter for E2B or Cloudflare behind the same interface, with a fake-SDK test like `tests/test_providers_offline.py`. Mark every API name you cannot verify against the package.
2. **A new hostile scenario.** Add an eleventh scenario to `lab/scenarios.py` (for example, a symlink to `/etc/passwd`, a DNS-based exfiltration, or a write to a mounted volume). Show what the bare world and the sandbox do, and say honestly where the mock is too simple to tell.
3. **A real run and a real number.** Run the task on one provider and report cold start (`create` to first `exec`), total time, and cost against the list-price arithmetic. Do not commit credentials or full logs.
4. **A policy.** Write the Day 36 decision for your own team: which workloads need which boundary, which tokens, which TTL, and what approval, in half a page.

### How you will be graded

| | Basic | Good | Excellent |
|---|---|---|---|
| **Threat model** | Lists threats | Maps each to what a sandbox gives | Also says what it does not solve, with a test |
| **Claims** | "Provider X is secure" | Each claim has a source | Separates docs, mock and assessment, as the page does |
| **Secrets** | Environment variables | Placeholders or brokering | Explains where the value lives for each provider and the blast radius if the agent is injected |
| **Cost** | Ignores it | Sets a TTL | Computes the cost of the timeout and compares it with a real bill |
| **Honesty** | Hides what was not run | Lists it | Lists it and says how to test it |

### Ask AI (use it as a reviewer, not an author)

- "Here is my sandbox spec. List what an injected agent could still reach, and what I would have to change to stop each one."
- "My allow-list includes `github.com`. How can an attacker still use that, and what limits it?"
- "Argue for and against running this on a hardened Kubernetes Job instead of a hosted sandbox. What would make you switch?"
- "Which of the claims in my comparison table could be checked with a script against a live account? Write the script."

Check anything it says about a provider against that provider's current documentation. These products change monthly; an answer from memory may describe a version that no longer exists.
