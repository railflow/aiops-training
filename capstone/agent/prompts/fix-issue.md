Task: fix one bug that is already reported in the issue tracker, and prove it with a test.

Repository issue: #${ISSUE_NUMBER}. Read it first (title, reproduction, failing test): the harness has put its text in ISSUE.md in the current directory.
Prompt version: ${PROMPT_VERSION}. Run id: ${AGENT_RUN_ID}.

Method:
1. Find the test named in the issue. Run it and confirm it fails for the reason the issue states. If you cannot reproduce it, stop and say so.
2. Make the smallest production change that fixes the cause (not the symptom). Do not refactor unrelated code.
3. Remove the expected-failure or skip marker that references this issue, so the test now runs and passes.
4. Run the whole suite. No other test may fail, and coverage must not drop.
5. Commit with a message that ends with `Fixes #${ISSUE_NUMBER}`.

Fixing production code IS allowed in this task, for this issue only.
