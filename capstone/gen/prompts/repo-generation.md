# Repo-generation prompt (parameterised)

Fill the `{{...}}` placeholders. Send it to a coding model in headless mode (see `gen_with_claude.sh`). Keep the temperature/effort low enough that
runs are comparable; remember that model output is NOT deterministic, so the answer key is part of the output you must validate.

---

You are generating a TRAINING repository for a DevEx course. It will be used to practise finding and fixing problems, so the problems are intentional.

Write a realistic **{{language}}** service for the domain **{{domain}}** ({{domain_description}}) in the current directory. Target about **{{target_loc}}** lines of
source code, split over at least {{min_files}} files with sensible package structure. It must build and its tests must run with the standard toolchain
({{build_command}} / {{test_command}}). Use a fixed random seed of {{seed}} for any choices you make.

Requirements:
1. Business logic that looks like a real service: validation, calculations, parsing, a repository/storage abstraction (in memory is fine), and a small CLI or HTTP handler.
2. Tests that cover only about 15 to 30 percent of the code. Tests that exist must pass, except exactly one deliberately flaky test.
3. Plant between {{min_bugs}} and {{max_bugs}} real defects, each different, chosen from: off-by-one, null/None handling, integer overflow, bad parsing,
   timezone mistakes, race conditions, missing input validation, resource leaks, wrong rounding, swallowed errors. Mix the severities.
   The defects must be subtle logic bugs that a good test would expose, not syntax errors, and the project must still compile.
4. Add code smells (long functions, duplication, magic numbers) and ONE use of a deprecated API.
5. Pin dependencies in the manifest, including at least one version with a known published vulnerability, and add a fake hardcoded credential
   (obviously fake, for example an access-key-shaped string you invent; never a real secret) in one source file.
6. Do not write comments that reveal the bugs. Do not mention that the code is a training exercise anywhere inside the repo.
7. Write `.planted-issues.json` in the REPO ROOT with EXACTLY this shape (the harness moves it out before the repo is published):
   {"repo": "{{name}}", "language": "{{language}}", "domain": "{{domain}}", "issues": [
     {"id": "{{name}}-P01", "file": "path/relative/to/root", "line_start": 10, "line_end": 14,
      "category": "off-by-one", "severity": "low|medium|high|critical", "description": "one sentence"} ] }
   The line numbers must be correct for the FINAL files. Re-read each file and verify them before you finish.
8. Finish by running the build and the tests once and printing the results. Do not fix the planted defects.
