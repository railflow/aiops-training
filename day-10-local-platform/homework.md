# Day 10: A local enterprise-like platform (Forgejo and Nexus): homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day10/`.

### Exercise 1: Diagram it

**Do:** draw (mermaid in a `platform.md`) the platform you built, including the two names for Nexus. Add one sentence per box on its corporate equivalent.

### Exercise 2: Issue to commit

**Do:** open an issue in Forgejo ("Add /healthz test"), make a branch, commit a change that references it (`Fixes #2` in the message), push, and open a pull request in the UI.

### Exercise 3: Break the runner

**Do:** scale the runner to zero (`kubectl -n platform scale deploy/forgejo-runner --replicas=0`), push a commit, and observe the run waits; scale it back and watch it pick the job up. Explain what a queue of waiting jobs looks like at 1000 repos.

### Exercise 4: Everything in Nexus

**Do:** list the image, jar, and wheel you published using the Nexus REST API (`/service/rest/v1/components`) and record the three listings.

### Exercise 5: Backups

**Do:** find where Forgejo and Nexus keep their data (`kubectl -n platform get pvc`) and write down what you would back up in a real company, and how often.
