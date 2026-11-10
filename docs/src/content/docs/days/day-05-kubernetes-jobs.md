---
title: "Day 5: Kubernetes Jobs"
description: "Files in day-05-kubernetes-jobs/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 5: Kubernetes Jobs"
  order: 5
---

This page is the file-by-file guide to [`day-05-kubernetes-jobs/`](https://github.com/railflow/aiops-training/tree/main/day-05-kubernetes-jobs) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: One-off, batch, migration, and scheduled work with Job and CronJob.

Homework for this day is in [`day-05-kubernetes-jobs/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-05-kubernetes-jobs/homework.md) and is repeated at the bottom of this page.

## What is in the folder

5 files. Paths below are relative to the repo root unless noted.

### day-05-kubernetes-jobs/jobs/

| File | What it is | How the lesson uses it |
|---|---|---|
| `jobs/cronjob-hello.yaml` | Writes a row every minute. Needs the Day 4 secret and image hello-py-app:1.0. Defines: CronJob `hello-cron`. | `cat day-05-kubernetes-jobs/jobs/cronjob-hello.yaml` |
| `jobs/job-db-seed.yaml` | Seeds the database: 5 successful runs in total, at most 2 at a time. Needs the secret from Day 4: kubectl create secret generic db-credentials --from-literal=PGPASSWORD="$DB_PASSWORD" Defines: Job `db-seed`. | `kubectl apply -f day-05-kubernetes-jobs/jobs/job-db-seed.yaml` |
| `jobs/job-fail.yaml` | A Job that always fails, to show retries, backoffLimit, and the Failed condition. Defines: Job `always-fails`. | `kubectl apply -f day-05-kubernetes-jobs/jobs/job-fail.yaml` |
| `jobs/job-hello-python.yaml` | Runs the Day 2 one-shot hello.py to completion. Compare with the Deployment that crash-looped in Day 3. Defines: Job `hello-python`. | `cat day-05-kubernetes-jobs/jobs/job-hello-python.yaml` |
| `jobs/job-migration.yaml` | A schema migration as a Job: the SQL lives in a ConfigMap, psql applies it. Written to be idempotent (IF NOT EXISTS), so running it twice is safe. Defines: ConfigMap `db-migrations`, Job `db-migrate-001`. | `cat day-05-kubernetes-jobs/jobs/job-migration.yaml` |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cat day-05-kubernetes-jobs/jobs/job-hello-python.yaml
kubectl apply -f day-05-kubernetes-jobs/jobs/job-hello-python.yaml
kubectl get jobs                                           # COMPLETIONS 0/1, then 1/1
kubectl get pods -l job-name=hello-python                  # STATUS Completed
kubectl logs job/hello-python                              # Hello, Job! from Python ...
kubectl describe job hello-python | tail -15
```

```bash
kubectl apply -f day-05-kubernetes-jobs/jobs/job-fail.yaml
kubectl get pods -l job-name=always-fails -w               # multiple pods: Error, with back-off between them; Ctrl+C
kubectl get job always-fails                               # COMPLETIONS 0/1
kubectl describe job always-fails | tail -12               # "BackoffLimitExceeded"
kubectl logs -l job-name=always-fails --tail=2
kubectl delete job always-fails
```

```bash
kubectl apply -f day-05-kubernetes-jobs/jobs/job-db-seed.yaml
kubectl get pods -l job-name=db-seed -w                    # see two pods at once; Ctrl+C when 5 are Completed
kubectl wait --for=condition=complete job/db-seed --timeout=180s
kubectl get job db-seed                                    # COMPLETIONS 5/5
kubectl -n data exec postgres-0 -- psql -U app -d app -c "select source, name, count(*) from greetings group by 1,2 order by 1,2;"
```

```bash
cat day-05-kubernetes-jobs/jobs/job-migration.yaml
kubectl apply -f day-05-kubernetes-jobs/jobs/job-migration.yaml
kubectl wait --for=condition=complete job/db-migrate-001 --timeout=120s
kubectl logs job/db-migrate-001
kubectl -n data exec postgres-0 -- psql -U app -d app -c "\d greetings" -c "select * from schema_migrations;"
```

```bash
kubectl delete job db-migrate-001
kubectl apply -f day-05-kubernetes-jobs/jobs/job-migration.yaml
kubectl logs job/db-migrate-001                            # "already exists, skipping": idempotent
```

## Expected output

The commands above carry their expected result in the `#` comment after them (for example `# COMPLETIONS 1/1`). A command that exits non-zero or prints an error means a step before it did not finish; check the earlier commands first.

## How these files relate to other days and shared tools

- Files from this folder are used by [Capstone](/days/capstone/), [Day 27](/days/day-27-durable-workflows-temporal/), [Day 30](/days/day-30-ai-agents-and-sandboxes/).

## Homework

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
