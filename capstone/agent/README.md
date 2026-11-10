# agent/: the sandboxed worker and the trusted grader

- `run-agent.sh`: clone, ONE headless `claude -p` session, quick checks, push a branch, print `RESULT {json}`. Never touches main, never merges.
- `evaluate.sh`: a separate trusted Job: integrity check, `build.sh measure`, gates. The agent never grades itself.
- `integrity_check.py`: deleted tests, fewer tests/assertions, trivial assertions, skips without an issue reference, production edits in a tests-only run.
- `bin/file_issue.py`: the only way to report a bug (dedupe by fingerprint, per-run cap, hidden marker for scoring).
- `prompts/`: system rules, coverage task, fix-issue task. Version them: the version is recorded per run.
- `job-agent.yaml.tpl`, `job-eval.yaml.tpl`: hardened Job templates. `Dockerfile`: the agent image.
