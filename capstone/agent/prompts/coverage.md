Task: raise unit-test coverage for this repository.

Target: line coverage of at least ${TARGET_COVERAGE} percent. Focus first on: ${FOCUS}.
Prompt version: ${PROMPT_VERSION}. Run id: ${AGENT_RUN_ID}.

Method:
1. Detect the stack (look for pom.xml, go.mod, package.json, requirements.txt, a .csproj). Run the existing tests once with coverage to see where you stand.
2. Pick the least-covered modules that contain real logic. For each public function write tests for: normal input, boundaries (empty, zero, one, max), invalid input, and the failure paths.
3. Prefer a few meaningful assertions per test over many trivial ones. A test must be able to fail if the code is wrong.
4. Run the new tests. For every failure apply rule 3 of your rules: it is a finding, not something to hide.
5. Commit after each module. Re-run the full suite at the end and report coverage before and after.

Fixing production code is NOT allowed in this task.
