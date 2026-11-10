---
description: Draft a new documentation page from a topic, following the style guide
argument-hint: <type: tutorial|how-to|reference|explanation> <topic>
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(build.sh docs:*)
---

Write a new documentation page. Arguments: $ARGUMENTS

1. Read `docs-as-code/style-guide.md` and one existing page of the same type to match structure.
2. Find the facts in the code, not from memory: grep the repository for the commands, flags and config keys you will mention.
3. Draft the page in `docs/` with front matter (`title`, `description`, `diataxis`).
4. Commands you cannot run here must be labelled "not run" or "example output". Do not invent flags: write "check the docs".
5. Run `build.sh docs` and fix broken links. Report what you verified and what you did not.
