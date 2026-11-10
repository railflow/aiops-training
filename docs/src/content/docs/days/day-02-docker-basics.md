---
title: "Day 2: Docker basics"
description: "Files in day-02-docker-basics/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 2: Docker basics"
  order: 2
---

This page is the file-by-file guide to [`day-02-docker-basics/`](https://github.com/railflow/aiops-training/tree/main/day-02-docker-basics) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Containers versus VMs, running and inspecting containers, building Python, Java, and Go images, layers and the build cache, and pushing to Docker Hub and a local registry.

Homework for this day is in [`day-02-docker-basics/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-02-docker-basics/homework.md) and is repeated at the bottom of this page.

## What is in the folder

18 files. Paths below are relative to the repo root unless noted.

### day-02-docker-basics/go-hello/

| File | What it is | How the lesson uses it |
|---|---|---|
| `go-hello/Dockerfile` | Stage 1: build a static binary with the Go toolchain. |  |
| `go-hello/go.mod` | Go module definition. |  |
| `go-hello/main.go` | Go program entry point (`main`). |  |

### day-02-docker-basics/java-hello/

| File | What it is | How the lesson uses it |
|---|---|---|
| `java-hello/Dockerfile` | Stage 1: compile with the full JDK. |  |
| `java-hello/Dockerfile.jlink` | Stage 1: compile, then use jlink to build a minimal Java runtime that contains only the modules this app needs (java.base is enough here). | `docker build -f Dockerfile.jlink -t hello-java:jlink .` |
| `java-hello/Hello.java` | Java source. Defines: `Hello`. |  |

### day-02-docker-basics/python-hello/

| File | What it is | How the lesson uses it |
|---|---|---|
| `python-hello/Dockerfile` | Container image recipe (base `python:3.12-slim`). |  |
| `python-hello/Dockerfile.app` | Container image recipe (base `python:3.12-slim`). |  |
| `python-hello/api.py` | A tiny REST API. |  |
| `python-hello/appwrite_hello.py` | Store and list 'hello' records in Appwrite using its REST API. |  |
| `python-hello/greeter.py` | Python module. Defines: `make_greeting`. |  |
| `python-hello/hello.py` | Python module. |  |
| `python-hello/hello_db.py` | Write one greeting row to Postgres and print the latest rows. |  |
| `python-hello/pytest.ini` | pytest settings for this folder. |  |
| `python-hello/requirements-dev.txt` | Pinned Python dependencies for this folder. |  |
| `python-hello/requirements.txt` | Pinned Python dependencies for this folder. |  |

### day-02-docker-basics/python-hello/tests/

| File | What it is | How the lesson uses it |
|---|---|---|
| `python-hello/tests/test_api.py` | Automated tests for api. |  |
| `python-hello/tests/test_greeter.py` | Automated tests for greeter. |  |

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-02-docker-basics/python-hello
cat Dockerfile
docker build -t hello-py:1.0 .
docker run --rm hello-py:1.0
docker run --rm -e NAME=Student hello-py:1.0
```

```bash
cd day-02-docker-basics/java-hello
docker build -t hello-java:1.0 .
docker build -f Dockerfile.jlink -t hello-java:jlink .
docker run --rm hello-java:1.0
docker run --rm hello-java:jlink
docker images hello-java
```

```bash
cd day-02-docker-basics/go-hello
docker build -t hello-go:1.0 .
docker run --rm hello-go:1.0
docker images hello-go
docker run --rm -it hello-go:1.0 sh
```

```bash
mkdir -p ~/heyjob-labs/day02 && cd ~/heyjob-labs/day02
cp -r day-02-docker-basics/python-hello day-02-docker-basics/java-hello day-02-docker-basics/go-hello .
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
FROM python:3.12-slim
...
 => [internal] load build definition from Dockerfile
 => [1/3] FROM docker.io/library/python:3.12-slim
 => [2/3] WORKDIR /app
 => [3/3] COPY hello.py .
 => exporting to image
Hello, world! from Python 3.12.x on 7c1d2e3f4a5b
Hello, Student! from Python 3.12.x on 9a8b7c6d5e4f
```

```text
Hello, world! from Java 21.0.x on 1a2b3c4d5e6f
Hello, world! from Java 21.0.x on 6f5e4d3c2b1a
REPOSITORY    TAG     IMAGE ID       CREATED          SIZE
hello-java    jlink   xxxxxxxxxxxx   20 seconds ago   ~110MB
hello-java    1.0     xxxxxxxxxxxx   1 minute ago     ~270MB
```

## How these files relate to other days and shared tools

- Builds on [Day 1](/days/day-01-getting-started/) (cluster, images or secrets created there).
- Files from this folder are used by [Day 1](/days/day-01-getting-started/), [Day 3](/days/day-03-kind-kubernetes/), [Day 4](/days/day-04-data-services-and-appwrite/), [Day 6](/days/day-06-networking-and-network-policy/), [Day 7](/days/day-07-traefik-ingress/), [Day 8](/days/day-08-security-and-supply-chain/), [Day 9](/days/day-09-build-tools-and-tests/), [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 14](/days/day-14-secrets-detection/), [Day 16](/days/day-16-secrets-management-openbao/), [Day 21](/days/day-21-is-my-app-up-gatus/).

## Homework

Work in `~/heyjob-labs/day02/`. Commit after each exercise.

```bash
mkdir -p ~/heyjob-labs/day02 && cd ~/heyjob-labs/day02
cp -r ~/aiops-training/day-02-docker-basics/python-hello ~/aiops-training/day-02-docker-basics/java-hello ~/aiops-training/day-02-docker-basics/go-hello .
```

### Exercise 1: Container lifecycle log

**Do:** with `nginx:1.27`, run a container `hw-web` on host port 8090 and record commands and outputs in `lifecycle.md`: start and `curl`; read logs; `docker exec` in and edit `/usr/share/nginx/html/index.html` to say `Hello <your name>`; `docker stop` then `docker start` and `curl`; `docker rm -f`, run again and `curl`; finally repeat with a **bind mount** (`-v "$(pwd)/site:/usr/share/nginx/html:ro"`) so the page survives removal.

**Deliverable:** `lifecycle.md` plus a 3-sentence explanation of why the edit survived `stop/start` but not `rm`.

### Exercise 2: Three images, compared

**Do:** build all four images (`hello-py:1.0`, `hello-java:1.0`, `hello-java:jlink`, `hello-go:1.0`) and make `sizes.md`, a table with image, size, layer count (`docker history IMAGE | wc -l` minus header), and "has a shell?".

**Deliverable:** `sizes.md` with real numbers plus a paragraph: which image is smallest and why, what did you give up, which would you choose for a production Go service.

### Exercise 3: Break and observe the build cache

**Do:** in your `python-hello` copy: (1) build `hello-py:cache1` twice and save the second log; (2) edit `hello.py` and rebuild as `cache2`; (3) add `RUN pip install --no-cache-dir flask==3.0.3` **above** `COPY hello.py .`, change `hello.py`, rebuild; then move the install **below** `COPY` and repeat. Compare times.

**Deliverable:** `cache.md` with trimmed logs and the rule you found, in your own words.

### Exercise 4: Registries

**Do:** start `registry:2`, tag and push `hello-go:1.0` and `hello-py:1.0` to it, prove it with `curl localhost:5000/v2/_catalog`; push `hello-py:1.0` to **your** Docker Hub account; delete the local copies and `docker pull` them back from each registry.

**Deliverable:** `registry.md` with commands, the catalog and tag-list output, and your Docker Hub repo URL.
