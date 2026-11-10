# Day 35: Durable AI agents with Eve: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Pick one:

1. **A new failure.** Add a scenario to `lab/crash-lab.mjs` the page does not cover (for example: the kill falls during the approval answer; two sessions for the same repository; the model returns an unknown tool name). Show it injected, what Eve did and what you would change.
2. **An exactly-once tool.** Make `git_commit` safe against being run twice with different content, and prove it with the naive and the safe version side by side.
3. **A real model.** Replace the scripted model with a real one for one repository. Report how it behaved after an `abandoned` call, and the cost of the run. Do not commit credentials.
4. **Versioning.** Change the agent's tool list between `eve build` runs while a session is parked. Report what happens when the session is answered, and which Eve doc says why.

### How you will be graded

| | Basic | Good | Excellent |
|---|---|---|---|
| **Claims** | "Eve is durable" | Each claim backed by a captured run | Separates docs, lab and assessment, as the page does |
| **Side effects** | Ignores them | Shows a duplicate | Shows a duplicate and the key that removes it |
| **Comparison** | Lists features | Compares who starts recovery and where the record lives | Adds a case where a different tool wins |
| **Honesty** | Hides what was not run | Lists it | Lists it and says how you would test it |
| **Evidence** | Prose | A transcript | A transcript plus a test that would fail if the behaviour changed |

### Ask AI (use it as a reviewer, not an author)

- "Here is my tool. If the process dies between the side effect and the recorded result, what happens on resume? Is the effect repeated?"
- "Argue the case against adopting a durable agent runtime for this job. What is the cheaper alternative?"
- "Which of the claims in my comparison table could be checked against the pinned version with a test, instead of the docs?"
- "My Eve app waits for a person for three days. What happens if I redeploy during the wait, on Vercel and off Vercel?"

Check anything it says about Eve against the sources listed at the top, and against a test on your pinned version. Eve is a release candidate; an answer from memory may describe a different version.
