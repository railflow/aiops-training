# Day 4: Data services and Appwrite: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

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
