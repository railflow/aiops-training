# Day 3: kind Kubernetes: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day03/`. Commit after each exercise.

### Exercise 1: Three apps, three Deployments

**Do:** run the three Deployments, then edit **your copy** of each YAML so `NAME` is your name and `LOOP_SECONDS` is `5`, and re-apply.

**Deliverable:** `day03/k8s/hello-*.yaml` and `day03/pods.txt` (`kubectl get deploy,pods -o wide` plus `kubectl logs -l app=... --tail=3` for each app).

### Exercise 2: Diagnose three failures

**Do:** on a copy of one deployment, cause each failure on purpose and record symptom, diagnosis command and key line, and fix: (1) `ImagePullBackOff` (wrong tag); (2) `CrashLoopBackOff` (one-shot program); (3) `Pending` (hint: `resources.requests.cpu: "100"`).

**Deliverable:** `day03/failures.md`, one section per failure with a one-sentence root cause.

### Exercise 3: Lifecycle and the shared folder

**Do:** prove `$SHARED_DIR` works both ways; stop/start and show PVC data survives; destroy, recreate with the config, and show PVC data is gone while `$SHARED_DIR` content remains. Fill a table: Deployment, PVC data, `$SHARED_DIR` file, `emptyDir` data against "survives stop/start?" and "survives destroy?".

### Exercise 4 (stretch): Ask Claude Code, then verify

**Do:** in `~/heyjob-labs`, ask `claude` to explain every field of `hello-python.yaml` in a table, and what happens if `imagePullPolicy` is removed (no edits). Check two claims yourself with `kubectl explain pod.spec.containers.imagePullPolicy` and one other.

**Deliverable:** `day03/claude-review.md` with the answer, the commands you used to verify, and any wrong or vague claims.
