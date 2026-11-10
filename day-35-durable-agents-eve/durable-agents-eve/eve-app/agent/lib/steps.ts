// The real work of each tool, free of any framework. The eve tools, the plain loop and the unit tests all call these.
import { ledger, maybeDie, pause, pullRequests, readRepo, savePullRequests, stepMs, writeRepo } from "./lab.ts";

export async function runTests(repo: string) {
  ledger({ event: "start", tool: "run_tests", repo });
  maybeDie("run_tests", "before");
  if (process.env.LAB_FAIL_REPO === repo) throw new Error(`test runner crashed for ${repo} (injected, permanent)`);
  await pause(stepMs());
  const coverage = Math.min(90, 40 + 25 * readRepo(repo).tests.length);
  maybeDie("run_tests", "after");
  ledger({ event: "done", tool: "run_tests", repo, coverage });
  return { repo, coverage };
}

export async function writeTestFile(repo: string) {
  ledger({ event: "start", tool: "write_test_file", repo });
  maybeDie("write_test_file", "before");
  await pause(stepMs());
  const state = readRepo(repo);
  // Idempotent on purpose: the file name is derived from the repo, so a repeat call rewrites the same file.
  const path = `tests/test_generated_${repo}.py`;
  if (!state.tests.includes(path)) state.tests.push(path);
  writeRepo(repo, state);
  maybeDie("write_test_file", "after");
  ledger({ event: "done", tool: "write_test_file", repo, path });
  return { repo, path };
}

export async function gitCommit(repo: string) {
  ledger({ event: "start", tool: "git_commit", repo });
  maybeDie("git_commit", "before");
  await pause(stepMs());
  writeRepo(repo, { ...readRepo(repo), committed: true });
  maybeDie("git_commit", "after");
  ledger({ event: "done", tool: "git_commit", repo });
  return { repo, branch: `agent/coverage-${repo}` };
}

/** `LAB_NO_IDEMPOTENCY=1` removes the dedupe check, to show what a repeated call does to a naive tool. */
export async function openPr(repo: string) {
  ledger({ event: "start", tool: "open_pr", repo });
  maybeDie("open_pr", "before");
  await pause(stepMs());
  const key = `coverage-pr:${repo}`;
  const prs = pullRequests();
  const existing = process.env.LAB_NO_IDEMPOTENCY ? undefined : prs.find((p) => p.key === key);
  if (!existing) savePullRequests([...prs, { repo, key }]);
  maybeDie("open_pr", "after");
  ledger({ event: "done", tool: "open_pr", repo, created: !existing });
  return { repo, key, created: !existing };
}
