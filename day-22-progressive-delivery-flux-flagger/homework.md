# Day 22: Release risk, GitOps with Flux, and progressive delivery with Flagger: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day22/`.

### Exercise 1: Rolling update math

**Do:** for 4 replicas, write the number of pods that can be unavailable and the maximum total during an update for `maxSurge: 50%, maxUnavailable: 0` and for `maxSurge: 0, maxUnavailable: 1`. Prove one of them with `kubectl get pods -w`.

### Exercise 2: A Flux-synced app

**Do:** add a second app (your own app, or the hello apps with the probes from Day 21) to `hello-config` under `apps/`, with its own Flux Kustomization.

### Exercise 3: A canary that promotes

**Do:** release a new version of your own app through the canary and record the weights in order.

### Exercise 4: A canary that rolls back, on purpose

**Do:** make a failing canary three different ways (HTTP 500s, slowness over the p99 limit, and a failing `pre-rollout` smoke test). 

### Exercise 5: Revert in git

**Do:** after an automatic rollback, use `git revert`, push, and show Flux reconcile to a state that matches the cluster.

### Exercise 6: Tell Keep

**Do:** configure a Flagger `event` webhook (or alert provider) that posts to Keep's `/alerts/event` when a canary fails.

### Exercise 7: Break it

**Do:** make the Flux Secret `forgejo-auth` wrong, push a change, and diagnose why nothing rolls out.
