# Day 13: CI at scale with a central build.sh: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day13/`.

### Exercise 1: Run `build.sh` on your three apps

**Do:** run `build.sh build test` for Python, Java, and Go (using Docker only where tools are missing). Save the three transcripts (`python.txt`, `java.txt`, `go.txt`).

### Exercise 2: Add a stack

**Do:** teach `build.sh` about a new stack: detect `Cargo.toml` (Rust) or `composer.json` (PHP) and add build/test commands. Update `usage` text. Keep the other stacks working (run the dry runs again).

### Exercise 3: Exit codes

**Do:** write a tiny test script (`test-build-sh.sh`) that asserts: unknown flag exits 2, undetectable stack exits 2, `--help` exits 0, a dry run exits 0. Run it.

### Exercise 4: Builder image in Nexus

**Do:** build, push, and pull the builder image through Nexus and write down its size and the time of a cold pull versus a cached pull on the runner.

### Exercise 5: DinD versus BuildKit

**Do:** write a half-page comparing DinD and BuildKit for a company with 1,000 repos: security, cache sharing, cost, failure modes, operations.
