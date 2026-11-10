# Day 12: Understanding dependencies: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day12/`.

### Exercise 1: Measure and record

**Do:** complete this table for all three projects: direct dependencies (count lines in the manifest), installed packages, size on disk, install time (cold), install time (warm cache).

### Exercise 2: Break a lock file

**Do:** edit `package-lock.json` (change a version number by hand), run `npm ci`, and record the error. Then restore it with `git checkout package-lock.json`. Repeat for `package.json` (change a version) and note the difference between `npm ci` and `npm install`.

### Exercise 3: Cache invalidation

**Do:** in the layered Dockerfile, edit only `index.js` and rebuild (fast), then add one dependency to `package.json` and rebuild (slow). Record both build times and which layers `docker build` reported as `CACHED`.

### Exercise 4: Find the biggest folder

**Do:** find the five largest packages inside `node_modules` and explain why they are large.

### Exercise 5: Why is the lock file not ignored?

**Do:** write five sentences explaining why `package-lock.json` is committed but `node_modules` is not. Include reproducibility, review (a lock file diff shows exactly what changed), CI speed, and the supply-chain angle.

### Exercise 6: Slow, flaky, risky

**Do:** list the three reasons from this page why a cold CI install is a problem and, for each, name the fix you tried (cache, baked image) and how well it worked in your own timings.
