# Day 20: Alerting and incident management with Keep: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day20/`.

### Exercise 1: Interview, then catalog

**Do:** write the interview questions for a **developer** and an **infrastructure engineer** (at least five each), "interview" two classmates or colleagues (or role-play both with an AI and then challenge its answers), and produce an alert catalog table with at least ten rows using the template above. Include two security alerts and one platform alert (node not ready) you will implement.

### Exercise 2: Two new alerts that fire and resolve

**Do:** implement two new alerts as ClickHouse queries and Keep workflows (for example error logs for a service in 5 minutes, and a node-condition alert), following the `fire` / `resolve` pattern. Trigger both with k6 or fault injection and capture the firing and resolved states.

### Exercise 3: Runbook and severity

**Do:** write a runbook for each new alert from `_template.md` and link it from the alert's `labels.runbook`. Assign severities and justify each in one sentence.

### Exercise 4: A notification sink and a captured payload

**Do:** point one alert at the echo sink and save the exact JSON it received. Then explain, in five lines, how you would map that payload to PagerDuty or Slack.

### Exercise 5: Escalation policy and rotation file

**Do:** write your own `schedule.json` for three people with one holiday override, run `rotate.py` for four different dates, and write the escalation policy in plain words (who, after how many minutes, and what "acknowledged" means).

### Exercise 6: Game day and blameless review

**Do:** run the game day from step 27 with a partner and write the review.

### Exercise 7: Break it

**Do:** recreate the `keep-providers` Secret with a **wrong ClickHouse password**, restart `keep-backend`, and diagnose from Keep's logs and ClickHouse's logs why the workflows fail. Then restore it.
