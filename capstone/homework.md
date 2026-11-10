# Capstone: the AI agent army: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

The capstone is one large assignment: generate 100+ messy repositories, put them in Forgejo, measure a baseline in ClickHouse, then build an autonomous, guard-railed fleet of AI agents orchestrated by Temporal that raises coverage, files real bugs, and proves its own benefit.

The full task text is on the course site. If you finish early, these stretch goals are part of the homework:

1. Add a Go or .NET toolchain and make the generated repos build; fix the generator.
2. Add mutation testing (mutmut or PIT) to `measure.py` as a new column, and make the agent's acceptance depend on it.
3. Replace the "same file, near the line" matcher with one that also uses the failing test name; report precision and recall per category.
4. Replace `KubernetesJobRunner` with a sandbox runner (Day 30, and Day 36 for three hosted options and a mock to test against) behind the same two methods.
5. Run the same 3 repos with two different model tiers and compare **cost per accepted coverage point**. Which was cheaper? Which tests were better?
