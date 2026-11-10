---
description: Compare the docs with the code and list or fix drift
argument-hint: [path to check, default whole repo]
allowed-tools: Read, Edit, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(build.sh docs:*)
---

Find documentation that no longer matches the code. Scope: $ARGUMENTS (default: the whole repository).

1. List recent code changes: `git log --since="30 days ago" --name-only --format=` and group by directory.
2. For each changed area, read the docs that describe it (README, runbook, architecture, API pages).
3. Report each mismatch as: file, the claim in the docs, the evidence in the code (file and line), and a proposed edit.
4. Apply edits only where the code is unambiguous. For anything else, leave a list for a human.
5. Run `build.sh docs`. Finish with: what you changed, what you left, and anything you could not verify.
