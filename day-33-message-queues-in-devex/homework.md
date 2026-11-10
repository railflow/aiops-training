# Day 33: Message queues, and why they matter in DevEx: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

**Pick one of these and time-box it to a couple of hours:**

1. **Your company's mess.** Choose two handoffs between teams that go through tickets or chat today (for example "new repo", "new test environment", "rotate a certificate"). For each, write the message contract: subject, envelope, payload schema, who publishes, who consumes, the failure paths. Draw it as a Mermaid diagram.
2. **Extend Lab 3.** Add one new request kind (for example `dns-record` to a human, `test-environment` to automation) to `routes.yaml`, with a test, and show it end to end with `./platform request`.
3. **Extend the capstone.** Replace the capstone's webhook receiver with a bus consumer that starts the same Temporal workflows, with the workflow id derived from the event id. Explain what you gain and what you lose.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Contracts** | Free-form text | Subjects, envelope and payload written down | Versioned schema (AsyncAPI or JSON Schema) with a compatibility rule |
| **Failure handling** | Happy path only | Retries and a dead-letter path | Idempotency argued per consumer, poison and ordering cases covered, a runbook |
| **Observability** | "We would log it" | Correlation id and one query | A dashboard or alert on queue age and time-in-state, with a threshold justified |
| **Honesty** | Everything "just works" | Names one trade-off | States when **not** to use a bus for this case, and what the cheaper alternative is |
| **Evidence** | Claims only | A test or captured run | Tests plus a failure injected on purpose |

### Ask AI (use it as a reviewer, not an author)

- "Here is my message contract. Which consumer would break if I add a required field? Which if I rename one?"
- "Here is my handler. Under at-least-once delivery, list every way it could double-apply an effect."
- "Argue the case **against** putting a message bus in this design. What is the simplest alternative?"
- "Given this routes.yaml, write five requests that fall through the rules in surprising ways."

Check anything it says against the NATS or CloudEvents documentation before you believe it.
