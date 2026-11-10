# Day 15: Guard rails and policy as code with OPA: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day15/`.

### Exercise 1: Three tested policies

**Do:** copy `day-15-guard-rails-and-opa/policies/` into your own `policies/` folder. Add a **fourth** rule of your choice (for example: only deploy images from your registry host, or deny the tag `latest`) with at least two tests (one allow, one deny).

### Exercise 2: Prove each rule blocks

**Do:** with `deploy.sh` and the OPA service (or `opa eval`), produce three denied runs, one for each original rule individually (only one input wrong each time), plus one allowed run. Save the four transcripts.

### Exercise 3: Time travel

**Do:** with `NOW_NS`, show the deploy allowed at Wednesday 20:00 PST, Wednesday 21:59 PST, and denied at Wednesday 22:00 PST and Wednesday 19:59 PST (compute the nanosecond values with `python3` and `zoneinfo`).

### Exercise 4: Exceptions with an expiry

**Do:** extend the coverage rule so a service named in `data.exceptions` (a JSON file with `{"hello-java": {"min_coverage": 5, "expires": "2027-01-01"}}`) uses its own lower threshold until the expiry date. Add tests for before and after the expiry.

### Exercise 5: Why not just a script?

**Do:** write 6-8 sentences: for a company with 1,000 repos, why is a central policy service better than a shared shell function? Cover testing, audit, exceptions, ownership, and the risk of a policy service outage.
