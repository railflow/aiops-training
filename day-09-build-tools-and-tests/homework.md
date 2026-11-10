# Day 9: Build tools, tests, and coverage: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day09/` (copy the reports there).

### Exercise 1: Phase by phase

**Do:** run `compile`, `test`, `package`, `verify` separately and, for each, list in `lifecycle.md` which new files appeared under `target/`.

### Exercise 2: Dependencies

**Do:** produce `dependency:tree`, find one transitive dependency, and find its folder in `~/.m2`. Add the `commons-lang3` dependency to the POM, re-run, and note what new folders appeared.

### Exercise 3: Raise Java coverage

**Do:** raise the Java coverage above 40%. `Api` is hard to test because it starts a server; refactor so the handlers can be called without a socket, or start the server on port 0 in a test. Keep logic out of I/O code.

### Exercise 4: The three reports

**Do:** collect `TEST-*.xml` and `jacoco.xml` (Java), `junit.xml` and `coverage.xml` (Python), and `cover.out` (Go). In `reports.md` explain which tool, in a pipeline, would read each.

### Exercise 5: Gradle versus Maven

**Do:** run the Gradle build and write five lines on what differed (files, time, output folders, console output).
