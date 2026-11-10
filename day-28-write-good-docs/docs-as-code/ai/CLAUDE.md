# CLAUDE.md (project memory for Claude Code)

Copy this to the root of a repository as `CLAUDE.md`. Claude Code reads it at the start of every session, so keep it short and true.

## What this repo is
<one paragraph: what it builds, stack, who owns it>

## Commands
- Build, test, scan: `build.sh build test secure`
- Docs gate and docs site: `build.sh docs`  (this template assumes the docs site lives in `docs/` of your repository; dev server: `cd docs && npm run dev`. A working example: `day-28-write-good-docs/docs-as-code/starlight-site/`)
- Run one test: <command>

## Documentation rules (read `docs-as-code/style-guide.md` first)
- A change to behaviour, configuration, an API or an operational procedure updates the docs **in the same commit or pull request**.
- If no doc change is needed, add a commit trailer: `Docs: n/a <reason>`. The CI docs gate checks for it.
- Every page has one Diataxis type. Runbooks never contain secrets: name the secret's location instead.
- Do not claim a command was run unless you ran it. Label un-run output "example output".
- When unsure of a flag, key, endpoint or version, write "check the docs" and link. Do not invent.

## Boundaries
- Never commit secrets or `.env` files. Never edit generated files in `dist/` or `.astro/`.
- Ask before adding a dependency or changing CI.
