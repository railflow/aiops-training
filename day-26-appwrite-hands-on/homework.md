# Day 26: Appwrite hands-on - functions, databases and a laptop-built app: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day26/`.

### Exercise 1: Function in a fourth language

**Do:** write the same hello function in PHP, Deno or Bun by following the runtime's starter template.
### Exercise 2: Break it, the timeout

**Do:** add a `sleep` longer than the function's timeout and execute it.
### Exercise 3: Least privilege

**Do:** give `write-row` the narrowest scopes that work, then remove one and read the failure.
### Exercise 4: Callback decision

**Do:** implement option A or B from Part 3 and show the probe turning green.
### Exercise 5: Switch the guestbook to the database

**Do:** set `STORE=appwrite` (and the endpoint variable), create entries, redeploy, and verify the rows in the console.
### Exercise 6: Rollback drill

**Do:** deploy a deliberately broken version of `guestbook`, watch the Gatus check go red, and roll back to the previous deployment.
### Exercise 7: A production swap, on paper

**Do:** write the values file that moves storage to an external S3 bucket (use `helm show values` and the chart's storage guide) without any real credentials in it.
