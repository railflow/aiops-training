# Day 14: Secrets, part 1: never commit them, and catch them when you do: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day14/`. Use only **fake** secrets, ever. The rest of the secrets homework (OpenBao, injection, rotation) is in Day 16.

### Exercise 1: Seed it and make the hook block it

**Do:** seed a fake AWS-style key and a fake password into a new file in a scratch repo, install the pre-commit hook, and capture the blocked commit.

### Exercise 2: `build.sh secure` fails, then passes

**Do:** run `build.sh secure` against the seeded repo (it must fail with exit code 1). Fix it for the **current tree** by moving the value to an environment variable, and re-run: the history scan still fails, so add a baseline for the existing finding and re-run.

### Exercise 3: False positive

**Do:** add a line to a test file containing the documented example value `AKIAIOSFODNN7EXAMPLE` (if your gitleaks version reports it) and allow it narrowly in a config file with a comment explaining why. Prove an unrelated fake key is **still** caught.

### Exercise 4: Recover and judge

**Do:** build the leaky image, recover the secret three ways, then write the corrected Dockerfile that reads the password at **runtime** (no `ENV`, no `COPY .env`). Prove with `docker history` and `docker run ... env` that the secret is gone.

### Exercise 5: Response plan

**Do:** write `leak-response.md`: the exact first five actions you take if an AWS key is found in a public repo, in order, and why rotation comes before history cleanup.
