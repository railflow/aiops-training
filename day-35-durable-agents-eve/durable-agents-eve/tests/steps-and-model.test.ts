import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { decide } from "../eve-app/agent/lib/scripted-model.ts";
import { gitCommit, openPr, runTests, writeTestFile } from "../eve-app/agent/lib/steps.ts";

const fresh = (env: Record<string, string> = {}) => {
  const dir = mkdtempSync(join(tmpdir(), "durable-agents-eve-test-"));
  for (const k of ["LAB_NO_IDEMPOTENCY", "LAB_FAIL_REPO", "LAB_DIE_AT", "LAB_STEP_MS"]) delete process.env[k];
  Object.assign(process.env, { LAB_DIR: dir, ...env });
  return dir;
};
const forge = (dir: string) => JSON.parse(readFileSync(join(dir, "forge.json"), "utf8"));

const user = (text: string) => ({ role: "user", content: [{ type: "text", text }] });
const result = (toolName: string, output: unknown) => ({ role: "tool", content: [{ type: "tool-result", toolCallId: toolName, toolName, output }] });
const ok = (toolName: string) => result(toolName, { type: "json", value: {} });

test("the scripted model follows the plan, one tool per turn, then stops", () => {
  const history: any[] = [user("plan=full repo=a-1")];
  const seen: string[] = [];
  for (let i = 0; i < 8; i++) {
    const d = decide(history);
    if ("text" in d) { assert.match(d.text, /finished a-1/); break; }
    seen.push(d.tool);
    history.push(ok(d.tool));
  }
  assert.deepEqual(seen, ["run_tests", "write_test_file", "run_tests", "git_commit", "open_pr"]);
});

test("the scripted model repeats a call whose result says it may not have taken effect", () => {
  const history = [user("plan=full repo=a-1"), ok("run_tests"), ok("write_test_file"), ok("run_tests"), ok("git_commit"),
    result("open_pr", { type: "text", value: "The step running this call was interrupted. The call may or may not have taken effect." })];
  const d = decide(history);
  assert.ok("tool" in d && d.tool === "open_pr");
});

test("the scripted model reports a failed tool and stops", () => {
  const d = decide([user("plan=full repo=a-1"), result("run_tests", { type: "error-text", value: "boom" })]);
  assert.ok("text" in d && d.text.startsWith("FAILED a-1"));
});

test("coverage rises after the test file is written", async () => {
  fresh();
  assert.equal((await runTests("a-1")).coverage, 40);
  await writeTestFile("a-1");
  assert.equal((await runTests("a-1")).coverage, 65);
});

test("writing the test file twice leaves one file", async () => {
  fresh();
  await writeTestFile("a-1");
  await writeTestFile("a-1");
  assert.equal((await runTests("a-1")).coverage, 65);
});

test("open_pr with a stable key creates one pull request however often it runs", async () => {
  const dir = fresh();
  await gitCommit("a-1");
  assert.equal((await openPr("a-1")).created, true);
  assert.equal((await openPr("a-1")).created, false);
  assert.equal(forge(dir).length, 1);
});

test("without the dedupe check a repeated open_pr opens two pull requests", async () => {
  const dir = fresh({ LAB_NO_IDEMPOTENCY: "1" });
  await openPr("a-1");
  await openPr("a-1");
  assert.equal(forge(dir).length, 2);
});

test("an injected permanent failure makes run_tests throw", async () => {
  fresh({ LAB_FAIL_REPO: "bad-1" });
  await assert.rejects(runTests("bad-1"), /injected, permanent/);
  assert.equal((await runTests("good-1")).coverage, 40);
});
