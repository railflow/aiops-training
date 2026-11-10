# Documentation style guide

The one page an AI agent (and a new human) reads before writing or editing a doc. Short on purpose.

## Voice

- Professional, direct, plain. Second person ("you"), present tense, active voice.
- Say what to do first, why second. One idea per paragraph.
- No jokes that need context, no hype words ("simply", "just", "easy", "powerful"), no profanity.
- Be honest about limits. If something was not run or not verified, say so. Never claim a command was run when it was not.
- When unsure of a flag, key, endpoint or version, write "check the docs" with a link. Do not invent.

## Structure (Diataxis)

Every page is exactly one of: **tutorial** (learning by doing), **how-to** (a task, steps), **reference** (facts, tables), **explanation** (why). Do not mix them in one page. Put the type in the front matter: `diataxis: how-to`.

## Mechanics

- Sentence-case headings. One H1 (the title). Do not skip heading levels.
- Code and commands in fenced blocks with a language tag; file, directory, function and flag names in `backticks`.
- Commands must be copy-pasteable and show the expected output in a separate block labelled as an example when you did not capture it live.
- Diagrams are Mermaid in a fenced block, with a sentence before it saying what to look at. Keep nodes under about 12.
- Links: relative, to the page, not to a URL you cannot check. No "click here".
- Tables for comparisons; lists for steps. Number only real sequences.
- Pin versions. Say which version the page was checked against and when.

## Never

- Secrets, tokens, passwords, private keys, internal-only URLs with credentials, real customer data. Name where a secret lives instead.
- Screenshots of terminals (use text), and text in images.
- "TODO" or "TBD" on a merged page. Open an issue and link it.

## Definition of done for a docs change

1. It builds (`build.sh docs`), and the link checker passes.
2. Every command in it was run, or is labelled as not run.
3. A reader who has never seen the system can follow it. Ask someone, or ask an agent to follow it literally and report where it got stuck.
