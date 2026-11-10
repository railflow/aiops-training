# Day 27: Durable workflows with Temporal: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Deliverables go in `~/heyjob-labs/day27/` (never commit credentials). Each has a self-check.

### Exercise 1: Run the bad script, kill it, document the loss
**Do:** run `month_end.py`, kill it in step 2 and again in step 4, and write what is lost each time.
### Exercise 2: Kill a worker, prove nothing finished was redone
**Do:** run the workflow with two workers (or two pods), kill the one running `generate_pdfs`, and export the event history.
### Exercise 3: Declarative retries
**Do:** make an activity fail three times (`IRS_FAIL_TIMES=3`) and read the retry policy in the UI.
### Exercise 4: A signal-based approval
**Do:** approve a batch from the CLI. Then **reject** another and read the compensation.
### Exercise 5: Convert one of your own scripts
**Do:** take a script you own (or use the template below). Split it into at least **three activities**, write a workflow with timeouts and a retry policy, and add **time-skipping tests**, including one where an activity fails twice.
### Exercise 6: Wire the dispatch job
**Do:** put `dispatch.yaml` in a repo on your Forgejo, fix the runner label and addresses, and make CI exit green while the workflow keeps running.
### Exercise 7: A Schedule
**Do:** create a Temporal Schedule for the monthly kickoff, trigger it manually, then pause it (`temporal schedule toggle --pause --reason ...`) and delete it.
### Exercise 8: Smell test, three scenarios
**Do:** for each, say "Temporal", "CI", "Job" or "CronJob", and why: (a) a nightly cache warm-up that is safe to run twice; (b) onboarding that emails on day 0, 3 and 7 and waits for a profile to be completed; (c) a 25-minute integration test suite.
### Exercise 9: The detour
**Do:** record `docker stats` memory before and after stopping a cluster you are not using. Optionally build the two-cluster lab and reach the shared service from `app-foo`.
### Exercise 10: Break it
**Do:** (a) put `datetime.now()` in workflow code and read the error; (b) set `start_to_close_timeout` far too low (1 second) on `generate_pdfs` and diagnose it **from the UI**.
