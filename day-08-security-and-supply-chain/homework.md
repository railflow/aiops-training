# Day 8: Vulnerabilities and the software supply chain: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day08/`.

### Exercise 1: Before and after

**Do:** scan `vuln-demo:1.0` and `vuln-demo:2.0` (HIGH and CRITICAL). Write `before-after.md` with both totals, the base images, and the three changes that mattered most.

### Exercise 2: Scan your own apps

**Do:** scan `hello-py-app:1.1` and `hello-java-app:1.1` from Day 6. Pick the worst finding for each and write what you would change. Do not change anything yet.

### Exercise 3: Two SBOMs

**Do:** generate CycloneDX and SPDX SBOMs for one of your apps and answer, with `jq`, "which version of `<some package>` is inside?" from each.

### Exercise 4: Signed and attested

**Do:** sign one of your app images by digest, attach its SBOM, and capture a successful verify and a failed verify (after altering the image).
