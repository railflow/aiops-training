# Day 23: Server and application patching: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day23/`.

### Exercise 1: Different scanners, different answers

**Do:** scan `patch-demo:1.0.0` with Trivy and with a second scanner (Grype, Docker Scout, or your IDE's), and list the differences.
### Exercise 2: An SBOM store

**Do:** write a script that, for every image your cluster runs, finds or generates its SBOM into one folder named by digest.
### Exercise 3: Renovate rules

**Do:** edit `renovate.json` so that patch updates of a dev-only tool automerge after CI passes, but runtime dependencies never do. Check the option names in the Renovate docs.
### Exercise 4: Break it with `:latest`

**Do:** change the deployment to `image: ...patch-demo:latest`, push an image tagged `latest` with the old pins, deploy, then push a fixed image to the **same** tag and watch what the cluster does (and what a node that already cached the old one does if `imagePullPolicy: IfNotPresent`).
### Exercise 5: A drain that cannot finish

**Do:** set the PodDisruptionBudget to `minAvailable: 3` with 3 replicas, then drain a node.
### Exercise 6: Write the rollback

**Do:** produce a rollback for patch 1.0.1: a `git revert`, and the observed result.
### Exercise 7: Mean time to patch

**Do:** record timestamps for detect, fix commit, merged, canary done, verified in your dry run, and compute the total.
