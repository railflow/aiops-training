# Day 5: Kubernetes Jobs: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day05/`. Commit after every exercise.

```bash
mkdir -p ~/heyjob-labs/day05/jobs && cd ~/heyjob-labs/day05
cp ~/aiops-training/day-05-kubernetes-jobs/jobs/*.yaml jobs/
```

---

### Exercise 1: Your own one-shot Job

**Do:** Write a Job manifest `jobs/hello-go.yaml` (from scratch, not copied) that runs your `hello-go:1.0` image **once** with `NAME` set to your name, `backoffLimit: 1`, and
`ttlSecondsAfterFinished: 300`. Apply it, read the log, then make a **failing variant** (for example point it at a command that exits 1) and observe the retries.

**Deliverable:** `jobs/hello-go.yaml` and `day05/job-notes.md` containing: `kubectl get job` output at start and end, the logs, and for the failing variant the number of pods created and the
condition reason shown by `kubectl describe job`.

---

### Exercise 2: Seed, then migrate

**Do:**
1. Run `job-db-seed.yaml` so the table has at least 5 `seed` rows. Change `completions` to 8 and `parallelism` to 4 in your copy and run it again (delete the old Job first).
   Watch how many pods run at a time.
2. Write a **new migration** `002_add_source_index.sql` (in a ConfigMap in your own manifest `jobs/job-migration-002.yaml`) that creates an index on `greetings(source)` and records version `002` in
   `schema_migrations`. It must be idempotent. Run it twice.

**Deliverable:** `day05/seed-and-migrate.md` with row counts, the pod-concurrency observation (e.g. `kubectl get pods -w` excerpt), and `\d greetings` plus
`select * from schema_migrations` after both migrations. Include your manifest.

---

### Exercise 3: A CronJob that ran

**Do:** Apply `cronjob-hello.yaml` and let it run until at least **two** scheduled Jobs have completed (do something else, such as reading Day 6, while you wait). Verify rows with `name='cron'`. Then **suspend** it and show it stops creating Jobs.
Extra: change the schedule to run every 2 minutes and set `concurrencyPolicy: Replace`; explain in one sentence what changes.

**Deliverable:** `day05/cron.md` with `kubectl get cronjob`, `kubectl get jobs` (showing at least two `hello-cron-...` Jobs), the SQL query output, and the suspend proof.

---

### Exercise 4: Pick the right object

**Do:** For each task, write **Deployment**, **Job**, or **CronJob** and a one-line reason, in `day05/choose.md`:

1. A REST API that serves customers.
2. A script that re-indexes search data every night at 01:30.
3. A one-time import of 50,000 rows from a CSV.
4. A worker that reads from a NATS stream forever.
5. A database migration that must succeed before a release.
6. A health-check script that pings a vendor API every 5 minutes.
7. Running the unit tests of your service on each commit.

**Deliverable:** `day05/choose.md`.

---
