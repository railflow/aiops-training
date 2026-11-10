# Day 25: Building an internal platform for hosting apps and APIs: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day25/`.

### Exercise 1: Extend the template

**Do:** add a Flagger `Canary` and an `IngressRoute` variant to `app-template/`, and make `platform new` accept `--lang go`.
### Exercise 2: A quota

**Do:** limit each app database's connections (`ALTER ROLE ... CONNECTION LIMIT n`) in `provision-db.sh`, with a comment explaining the number.
### Exercise 3: Row-level isolation proof

**Do:** show that role `alpha` cannot read database `beta` (`psql` error text in your notes) and that `PUBLIC` has no connect privilege.
### Exercise 4: Decide, in writing

**Do:** write a one-page decision for a hypothetical app with strict compliance needs: shared Postgres, dedicated Postgres, or managed service.
### Exercise 5: Break it, a noisy neighbour

**Do:** run a deliberately heavy query in one database (for example a large `generate_series` cross join) and watch another database's latency with a simple `pgbench` or timing loop.
### Exercise 6: Appwrite hardening review

**Do:** read the Appwrite chart's security and production guides and list five settings you would change before real users. Cite the page.
### Exercise 7: Review an AI-built dashboard

**Do:** have an assistant generate the dashboard from step 15, then review it with the checklist and fix at least two problems.
