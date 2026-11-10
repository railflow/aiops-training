# Day 34: Building an agent harness with Google ADK: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

**Pick one and time-box it to a couple of hours:**

1. **A case the catalogue does not have.** Think of a failure this harness does not handle (a node drain during the PR step, a repository whose tests need a database, a model that returns plausible but wrong paths). Add it to `common/faults.py`, write a failing test, handle it in **both** engines, and add a `# >> C19` marker so the counter picks it up.
2. **Port the pipeline to a `Workflow`.** Use ADK 2.0's graph-based workflow instead of `SequentialAgent` and `LoopAgent`, give the nodes `retry_config` and timeouts, and keep the tests green. Report what got simpler and what the deprecation warning's note about `LlmAgent` sub-agents cost you.
3. **Take the state off the node.** Replace the `hostPath` volume and the SQLite session file with a PersistentVolumeClaim, or with a database session service (this needs the `db` extra). Show that a retry on a **different node** still resumes.
4. **The decision memo.** One page: for the capstone's agent fleet, would you use a hand-rolled loop, ADK, ADK inside Temporal activities, or something else? Use the "what it took over" table as evidence and name what would change your mind.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Cases** | Names two or three | Maps each failure to a handler and a test | Finds a case not in the table and shows it injected and survived |
| **Honesty** | "ADK handles it" | Separates plumbing from policy | Tests the claim against the pinned version instead of the docs alone |
| **Resume** | Restarts from zero | Resumes state | Resumes state **and** the working tree, and says what is lost |
| **Cost** | No numbers | Counts tokens or lines | Compares engines on the same run, and says what the mock hides |
| **Evidence** | Claims only | A test or captured run | Tests plus a failure injected on purpose |

### Ask AI (use it as a reviewer, not an author)

- "Here is my agent loop. List every way it can run forever, spend unbounded money, or report success without doing the work."
- "Here is my Job manifest. What happens when the node is drained, the pod is OOM-killed, or the orchestrator restarts?"
- "Argue the case **against** adding an agent framework to this. What is the cheaper alternative?"
- "Given this ADK pipeline, which behaviour would change if I upgraded from 2.13.0 to the next minor version, and how would I find out before production?"

Check anything it says about ADK against [adk.dev](https://adk.dev/) and, better, against a test on your pinned version.
