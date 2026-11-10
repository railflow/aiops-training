# Day 31: Quality: specs, evals and decision models: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

1. **A real spec.** Write a spec for a real change in your team's repo and have an agent implement it. Record: how many times you had to correct it, which criteria it missed, and whether the checker would have flagged a weakness earlier.
2. **A real eval.** Build ten tasks from your own incident or PR history with deterministic checks. Run two models three times each. Report pass rate and cost per pass, and say what you would change in how you assign tasks to tiers.
3. **A real decision.** Pick one yes/no judgement your team makes repeatedly. Label 100 historical cases. Run a decision backend, choose `hi` and `lo` from the data, and report precision, recall and the human-review share. State what a wrong automatic decision costs.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Spec** | Prose wish | All sections, checker passes | Acceptance criteria map to named tests; non-goals prevented a real scope creep |
| **Eval design** | Tasks invented for the demo | Tasks from real work with deterministic checks | Held-out set, repeats, cost per pass, version and date recorded |
| **Decision policy** | One threshold chosen by feel | Thresholds chosen from a sweep | Review band sized against stated costs of each error; plan to feed human labels back |
| **Honesty** | Claims "AI works" | Reports numbers | Reports uncertainty, sample sizes, and what was not measured |
