---
description: Review a docs change against the style guide and try to follow it literally
argument-hint: <file or pull request branch>
allowed-tools: Read, Grep, Glob, Bash(git diff:*)
---

Review the documentation change in: $ARGUMENTS

Check, in order: (1) one Diataxis type per page; (2) secrets or internal-only details; (3) every command is runnable as written, or labelled; (4) claims of "I ran this" are plausible and not just asserted; (5) links are relative and valid; (6) tone matches `docs-as-code/style-guide.md`.
Then follow the steps literally as a newcomer and report the first place you got stuck.
Output a short list: blocking issues, suggestions, and questions. Do not edit files.
