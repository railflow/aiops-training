# Day 21: Is my app up and OK? Health endpoints, probes and Gatus: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day21/`.

### Exercise 1: Endpoints and probes in your own app

**Do:** add `/healthz`, `/readyz` and `/version` to one of your own apps (not just the hello apps) and give its Deployment startup, liveness and readiness probes. Write one test for each endpoint, including a failing readiness test.

### Exercise 2: Three Gatus endpoints

**Do:** add three endpoints to `config.yaml` for your app: a health check, a version assertion (`[BODY].version == ...`), and one **business** check with a response-time condition. Use a Service DNS URL for one and the Traefik `Host` header for another.

### Exercise 3: Fail one on purpose

**Do:** make one endpoint fail (wrong version string, or scale the app to zero) and capture the Gatus log lines for failure and recovery.

### Exercise 4: Webhook to Keep

**Do:** verify the Gatus failure arrives in Keep as a firing alert and later resolves.

### Exercise 5: Deduplicate with a ClickHouse alert

**Do:** cause a failure that both a ClickHouse alert and a Gatus alert detect, and show them in a single Keep incident through a correlation rule. Then decide whether the notification should fire per alert or per incident and implement your choice.

### Exercise 6: Tune against flapping

**Do:** make `hello-java` slow on purpose (for example `INJECT`-style delay or a small CPU limit) so its response time hovers around the threshold. Tune `failure-threshold`, `success-threshold`, `interval` and the condition until it neither pages on a blip nor misses a real outage.

### Exercise 7: Break it

**Do:** replace the `gatus-keep` Secret with a **wrong** API key, restart Gatus, make an endpoint fail, and diagnose from Gatus's logs why no alert appeared in Keep.
