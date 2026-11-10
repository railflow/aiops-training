---
title: "Day 4: Data services and Appwrite"
description: "Files in day-04-data-services-and-appwrite/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 4: Data services and Appwrite"
  order: 4
---

This page is the file-by-file guide to [`day-04-data-services-and-appwrite/`](https://github.com/railflow/aiops-training/tree/main/day-04-data-services-and-appwrite) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Run Postgres, MinIO, and NATS JetStream on kind, write rows from Python and Java, then build against a local Appwrite.

Homework for this day is in [`day-04-data-services-and-appwrite/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-04-data-services-and-appwrite/homework.md) and is repeated at the bottom of this page.

## What is in the folder

12 files. Paths below are relative to the repo root unless noted.

### day-04-data-services-and-appwrite/data/

| File | What it is | How the lesson uses it |
|---|---|---|
| `data/00-namespace.yaml` | Kubernetes manifest defining Namespace `data`. |  |
| `data/hello-db-pods.yaml` | One-shot pods that write a row to Postgres. Day 5 turns these into Jobs. Needs: kubectl create secret generic db-credentials --from-literal=PGPASSWORD="$DB_PASSWORD" Defines: Pod `hello-db-python`, Pod `hello-db-java`. | `kubectl apply -f day-04-data-services-and-appwrite/data/hello-db-pods.yaml` |
| `data/minio.yaml` | Create the secret first (see day04): kubectl -n data create secret generic minio-credentials \ --from-literal=MINIO_ROOT_USER=minioadmin \ --from-literal=MINIO_ROOT_PASSWORD="$MINIO_PASSWORD" (MinIO requires a root password of at least 8 characters.) Defines: | `kubectl apply -f day-04-data-services-and-appwrite/data/minio.yaml` |
| `data/nats.yaml` | NATS with JetStream (persistent streams) enabled via -js and a file store on a PVC. Defines: PersistentVolumeClaim `nats-data`, Service `nats`, Deployment `nats`. | `kubectl apply -f day-04-data-services-and-appwrite/data/nats.yaml` |
| `data/postgres.yaml` | Create the secret first (see day04): kubectl -n data create secret generic postgres-credentials --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" Defines: Service `postgres`, StatefulSet `postgres`. |  |

### day-04-data-services-and-appwrite/java-app/

| File | What it is | How the lesson uses it |
|---|---|---|
| `java-app/Dockerfile` | Stage 1: Maven build. Copying pom.xml first lets Docker cache the dependency download until the pom changes (see Day 2: put rarely-changing steps first). |  |
| `java-app/pom.xml` | Maven build file: dependencies and build plugins. | `cat day-04-data-services-and-appwrite/java-app/pom.xml \| head -40` |

### day-04-data-services-and-appwrite/java-app/src/

| File | What it is | How the lesson uses it |
|---|---|---|
| `java-app/src/main/java/com/example/Api.java` | Java source. Defines: `Api`. |  |
| `java-app/src/main/java/com/example/Greeter.java` | Java source. Defines: `Greeter`. |  |
| `java-app/src/main/java/com/example/HelloDb.java` | Java source. Defines: `HelloDb`. | `cat day-04-data-services-and-appwrite/java-app/src/main/java/com/example/HelloDb.java` |
| `java-app/src/test/java/com/example/ApiHelpersTest.java` | Java source. Defines: `ApiHelpersTest`. |  |
| `java-app/src/test/java/com/example/GreeterTest.java` | Java source. Defines: `GreeterTest`. |  |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cat day-02-docker-basics/python-hello/hello_db.py
cat day-02-docker-basics/python-hello/requirements.txt
cat day-02-docker-basics/python-hello/Dockerfile.app
```

```bash
docker build -f day-02-docker-basics/python-hello/Dockerfile.app -t hello-py-app:1.0 day-02-docker-basics/python-hello
kind load docker-image hello-py-app:1.0 --name ai-ops-training
```

```bash
cat day-04-data-services-and-appwrite/java-app/pom.xml | head -40
cat day-04-data-services-and-appwrite/java-app/src/main/java/com/example/HelloDb.java
docker build -t hello-java-app:1.0 day-04-data-services-and-appwrite/java-app
kind load docker-image hello-java-app:1.0 --name ai-ops-training
```

```bash
kubectl apply -f day-04-data-services-and-appwrite/data/hello-db-pods.yaml
kubectl get pods -w                                   # Ctrl+C when both show Completed
kubectl logs hello-db-python
kubectl logs hello-db-java
```

```bash
read -rsp "Choose a throwaway MinIO password (8+ chars): " MINIO_PASSWORD; echo
kubectl -n data create secret generic minio-credentials \
--from-literal=MINIO_ROOT_USER=minioadmin \
--from-literal=MINIO_ROOT_PASSWORD="$MINIO_PASSWORD"
kubectl apply -f day-04-data-services-and-appwrite/data/minio.yaml
kubectl -n data rollout status deploy/minio
```

## Expected output

The commands above carry their expected result in the `#` comment after them (for example `# COMPLETIONS 1/1`). A command that exits non-zero or prints an error means a step before it did not finish; check the earlier commands first.

## How these files relate to other days and shared tools

- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- Files from this folder are used by [Day 6](/days/day-06-networking-and-network-policy/), [Day 7](/days/day-07-traefik-ingress/), [Day 9](/days/day-09-build-tools-and-tests/), [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 14](/days/day-14-secrets-detection/), [Day 15](/days/day-15-guard-rails-and-opa/), [Day 16](/days/day-16-secrets-management-openbao/), [Day 21](/days/day-21-is-my-app-up-gatus/), [Day 25](/days/day-25-internal-platform/), [Day 33](/days/day-33-message-queues-in-devex/).

## Homework

Work in `~/heyjob-labs/day04/`. Commit after every exercise. Never commit passwords, `.env` files, or Appwrite keys.

```bash
mkdir -p ~/heyjob-labs/day04 && cd ~/heyjob-labs/day04
```

---

### Exercise 1: Rows from two languages

**Do:** Run the Python and Java writers (the lab) at least **three times each** with different `NAME` values (edit a copy of `hello-db-pods.yaml`, or use
`kubectl run ... --env NAME=...`). Then query Postgres.

**Deliverable:** `day04/rows.txt` containing the output of this query, plus `day04/queries.sql` with **three** queries you wrote yourself:
(1) count of rows per `source`, (2) the newest row per `source`, (3) rows created in the last 10 minutes.

```bash
kubectl -n data exec postgres-0 -- psql -U app -d app -c "select id, source, name, message, created_at from greetings order by id;" > ~/heyjob-labs/day04/rows.txt
```

---

### Exercise 2: Prove durability, and then break it

**Do:**
1. Delete `postgres-0` and show the row count is unchanged.
2. Delete the **StatefulSet and the pod but keep the PVC** (`kubectl -n data delete statefulset postgres`), recreate it from `postgres.yaml`, and show the data is still there.
3. Now delete the PVC (`kubectl -n data delete pvc data-postgres-0`) and recreate. Show the table is gone.

**Deliverable:** `day04/durability.md`: the commands, the row counts at each step, and 3-4 sentences explaining which object owns the data and why.

---

### Exercise 3: MinIO and JetStream

**Do:**
1. In MinIO, create a bucket named `homework`, upload **two** objects (one text file, one image from your laptop via the console), and list them with `mc ls`.
2. In JetStream, create a stream `HW` for subjects `hw.>`, publish 5 messages, and read them back with `nats stream view HW`. Delete the NATS pod and show the messages still exist.

**Deliverable:** `day04/object-and-stream.md` containing the commands and outputs of `mc ls local/homework`, `nats stream info HW`, and `nats stream view HW` (before and after pod deletion).

---

### Exercise 4: Appwrite records

**Do:** With Appwrite running, create **five** records using `appwrite_hello.py` (three from your laptop, two from a pod in the cluster). Create a second collection in the console
called `notes` with attributes of your choice (for example `title` and `body`), and add one document **in the console**.

**Deliverable:** `day04/appwrite.md` with: the output of `python appwrite_hello.py list` (redact nothing sensitive: it only prints ids, names, and messages), a screenshot or
description of the console page for `notes`, and one paragraph: *What would you have had to build yourself if Appwrite did not exist?*

---

### Exercise 5 (stretch): Python writes to MinIO

**Do:** Ask Claude Code to extend `hello_db.py` so it also uploads a small JSON file describing the new row to the `homework` bucket (hint: the `minio` Python
package, endpoint `minio.data:9000`, credentials from a Secret). Review the diff before accepting it; run it as a pod.

**Deliverable:** your changed script, the prompt you gave, and the `mc ls` output showing the new object.

---
