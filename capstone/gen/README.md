# gen/: make the mess

- `generate.py`: deterministic, free, no model. `--count 5 --seed 42` gives five repos (python, node, java, go, dotnet), each with planted bugs, a fake hardcoded secret, vulnerable pins, a flaky test and a small git history. Answer keys go to `../answer-keys/`, **outside** the repos.
- `make-samples.sh`: runs it into `../work/` (git-ignored) and writes `repos.csv`.
- `prompts/repo-generation.md` + `gen_with_claude.sh`: the AI route for larger, more realistic repos (about 10K LOC). Costs real money; start with one.
- `validate_repo.sh REPO KEY`: builds, tests, checks coverage is poor and the key's line numbers are real.
- `answer_key.py`: load keys into ClickHouse, match filed issues against them (`score`).

Domains (12): inventory, billing, csv-importer, url-shortener, booking, payroll, shipping, ticketing, loyalty, catalog, scheduler, notifications.
Size: `--filler N` adds N generated helper functions (about 10 lines each): `--filler 800` is roughly 8-9K lines per repo.
