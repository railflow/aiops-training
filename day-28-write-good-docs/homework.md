# Day 28: Writing good docs (and keeping them true): homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Deliverables go in `~/heyjob-labs/day28/`. Each has a self-check.

### Exercise 1: Classify
**Do:** take five pages of this course (or your own repo) and label each as tutorial, how-to, reference or explanation; for any that mix types, say how you would split them.
### Exercise 2: Break a link on purpose
**Do:** in `day-28-write-good-docs/docs-as-code/starlight-site/` (or your own site, after adding `starlight-links-validator`) break an internal link, run `npm run build`, read the report, fix it.
### Exercise 3: A real runbook
**Do:** write the runbook for one of your own services from `app-docs-template/docs/runbook.md`. Give it to a colleague (or an agent with `/doc-review`) and ask them to follow it literally.
### Exercise 4: Three ADRs
**Do:** write three short ADRs for decisions already made (a database choice, a base image, a deployment tool).
### Exercise 5: Tame an agent
**Do:** have an agent write a how-to page with `/doc-page`. Then find **three** things it got wrong or could not know (a flag, a version, a path).
### Exercise 6: The gate in your repo
**Do:** copy `check-docs-touched.sh` into a repository you own and wire it as a required check on pull requests. Open one pull request that fails and one that passes.
### Exercise 7: Deploy the docs
**Do:** build the example docs image (or one from your own site), run it on the cluster at `docs.localhost:8080`, add the Gatus check, and read three JSON log lines from `kubectl -n docs logs deploy/docs`.
### Exercise 8: Freshness
**Do:** run `doc-sync` against your repository by hand (not in CI).
