---
title: "Day 9: Build tools, tests, and coverage"
description: "Files in day-09-build-tools-and-tests/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 9: Build tools, tests, and coverage"
  order: 9
---

This page is the file-by-file guide to [`day-09-build-tools-and-tests/`](https://github.com/railflow/aiops-training/tree/main/day-09-build-tools-and-tests) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Maven and Gradle lifecycles, dependency resolution, JUnit, JaCoCo, pytest with coverage, go test, and the report files CI will collect.

Homework for this day is in [`day-09-build-tools-and-tests/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-09-build-tools-and-tests/homework.md) and is repeated at the bottom of this page.

## What is in the folder

2 files. Paths below are relative to the repo root unless noted.

### day-09-build-tools-and-tests/gradle-demo/

| File | What it is | How the lesson uses it |
|---|---|---|
| `gradle-demo/build.gradle` | The same Java sources as ../../day-04-data-services-and-appwrite/java-app, built with Gradle instead of Maven. | `cat build.gradle` |
| `gradle-demo/settings.gradle` | Support file. |  |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

From [Day 7](/days/day-07-traefik-ingress/): `day-07-traefik-ingress/` (`go-api/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd day-04-data-services-and-appwrite/java-app
ls -R src | head -20
cat src/test/java/com/example/GreeterTest.java
```

```bash
cd day-09-build-tools-and-tests/gradle-demo
cat build.gradle
docker run --rm -v "$PWD/..":/work -w /work/gradle-demo gradle:8.10-jdk21 gradle --no-daemon test jacocoTestReport
ls build/reports build/test-results/test
```

```powershell
cd day-02-docker-basics/python-hello
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing --cov-report=xml --cov-report=html --junitxml=junit.xml
```

```bash
cd day-02-docker-basics/python-hello
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing --cov-report=xml --cov-report=html --junitxml=junit.xml
```

```bash
cd day-07-traefik-ingress/go-api
docker run --rm -v "$PWD":/src -w /src golang:1.23 sh -c "go test -v -cover -coverprofile=cover.out ./... && go tool cover -func=cover.out"
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
src:
main  test
src/main:
java
src/main/java/com/example:
Api.java  Greeter.java  HelloDb.java
...
```

```text
> Task :compileJava
> Task :test
> Task :jacocoTestReport
BUILD SUCCESSFUL in 38s
build/reports: jacoco  tests
build/test-results/test: TEST-com.example.GreeterTest.xml ...
```

## How these files relate to other days and shared tools

- Builds on [Day 2](/days/day-02-docker-basics/), [Day 6](/days/day-06-networking-and-network-policy/) (cluster, images or secrets created there).
- Refers to files in [Day 4](/days/day-04-data-services-and-appwrite/) (for example from `day-09-build-tools-and-tests/gradle-demo/build.gradle`).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- The lesson also uses files from [Day 7](/days/day-07-traefik-ingress/).
- Files from this folder are used by [Day 12](/days/day-12-understanding-dependencies/), [Day 31](/days/day-31-ai-quality-specs-evals-decisions/).

## Homework

Work in `~/heyjob-labs/day09/` (copy the reports there).

### Exercise 1: Phase by phase

**Do:** run `compile`, `test`, `package`, `verify` separately and, for each, list in `lifecycle.md` which new files appeared under `target/`.

### Exercise 2: Dependencies

**Do:** produce `dependency:tree`, find one transitive dependency, and find its folder in `~/.m2`. Add the `commons-lang3` dependency to the POM, re-run, and note what new folders appeared.

### Exercise 3: Raise Java coverage

**Do:** raise the Java coverage above 40%. `Api` is hard to test because it starts a server; refactor so the handlers can be called without a socket, or start the server on port 0 in a test. Keep logic out of I/O code.

### Exercise 4: The three reports

**Do:** collect `TEST-*.xml` and `jacoco.xml` (Java), `junit.xml` and `coverage.xml` (Python), and `cover.out` (Go). In `reports.md` explain which tool, in a pipeline, would read each.

### Exercise 5: Gradle versus Maven

**Do:** run the Gradle build and write five lines on what differed (files, time, output folders, console output).
