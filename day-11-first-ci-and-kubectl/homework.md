# Day 11: Your first CI pipeline, and how kubectl really works: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day11/`.

### Exercise 1: Review Claude's workflow

**Do:** ask Claude Code for a workflow for the **Go** app (`go-api`), then review it with the checklist. Record, in `review.md`, three things you changed or rejected and why.

### Exercise 2: Timing table

**Do:** run the Python pipeline three times (push an empty commit with `git commit --allow-empty`). Record per-step times in `timing.md`.

### Exercise 3: Go and Java pipelines

**Do:** write `go-ci.yaml` and `java-ci.yaml` (tests, coverage, image build, push). For Java use `mvn -B verify` and archive the surefire and JaCoCo reports.

### Exercise 4: kubectl detective

**Do:** with `-v=8`, find the exact URL and HTTP method kubectl uses for `kubectl -n apps delete pod <name>` and for `kubectl -n apps scale deploy hello-py-ci --replicas=1`. Put both in `kubectl-internals.md`.

### Exercise 5: Make it fail safely

**Do:** add `--exit-code 1 --severity CRITICAL` to the image scan, push the **vulnerable** image from Day 8 as a test, confirm the pipeline stops before the push step, then revert.
