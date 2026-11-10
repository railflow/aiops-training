# Day 30: Agents and sandboxes: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

**Design a sandbox for your company.** In one to two pages, with a Mermaid diagram:

1. Pick a pattern from the decision table for each of: (a) a public open-source repo, (b) an internal service repo, (c) a repo that processes customer data. Justify with the questions in the table.
2. List what each sandbox may reach (network destinations, secrets, repos) and how each is enforced. Name the per-run token and its scope.
3. Say how the sandbox is started, watched and killed (Temporal, the bus, a Job controller) and what happens if the orchestrator dies.
4. List five ways it could still fail, and for each a detection or a limit.
5. Describe the skills registry for your team: owners, review, prune policy and the CI checks you would add beyond `check_skills.py`.

### How you will be graded

| Criterion | Weak | Good | Excellent |
|---|---|---|---|
| **Pattern choice** | One pattern for everything | Pattern per risk level | Justified by data sensitivity, hostile-input risk and what you can operate; admits what you cannot get (for example KVM) |
| **Isolation detail** | "Use a container" | Network, secrets, filesystem, identity each addressed | Each control has an enforcement point (policy, manifest, runtime) and a test or lint |
| **Failure thinking** | Happy path | Several failures listed | Residual risk stated honestly; detection and kill switch described |
| **Skills** | Not covered | Owners and CI checks | Prune policy with usage data, supply-chain stance, human review step |
| **Honesty** | Vendor claims repeated | Sources cited | Separates "documented", "we ran it" and "we assume" |
