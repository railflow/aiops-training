# Day 16: Secrets, part 2: where secrets live (OpenBao), how apps get them, and rotation: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day16/`. Use only generated, throwaway values.

### Exercise 1: Least privilege

**Do:** write a second policy that can read `secret/data/other-team/*` only, and a role that binds it to a ServiceAccount `other` in a namespace `other`. Prove with a SecretStore in `other` that it **cannot** read `hello-app/db`.

### Exercise 2: Rotation timeline

**Do:** run the rotation script while `curl` runs every 2 seconds against both apps. Record when each app's first `200` returns.

### Exercise 3: Shorten the window

**Do:** change `refreshInterval` to `10s`, repeat, and compare. Then write down why you would not set it to `1s` against a real secret store (API load, rate limits, cost).

### Exercise 4: Make the env-var app recover

**Do:** make `hello-py-env` pick up the new password **without** manual commands. Options: add the Reloader controller annotation, or switch it to a file. Pick one and justify it.

### Exercise 5: Dynamic credentials (optional)

**Do:** follow the OpenBao database secrets engine documentation to create a role for Postgres with a 5-minute lease, request credentials twice, and list the users in Postgres (`\du`).
