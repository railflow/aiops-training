import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

const loop = join(import.meta.dirname, "..", "plain", "plain-loop.ts");
const run = (dir: string, env: Record<string, string> = {}) =>
  spawnSync(process.execPath, [loop, "a-1"], { env: { ...process.env, LAB_DIR: dir, LAB_APPROVAL_WAIT_MS: "1500", ...env }, encoding: "utf8" });
const approve = (dir: string) => { mkdirSync(join(dir, "approvals"), { recursive: true }); writeFileSync(join(dir, "approvals", "a-1"), "x"); };
const events = (dir: string) => readFileSync(join(dir, "ledger.jsonl"), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));

test("a plain loop that dies after its approval was consumed starts over from step 1 and needs a second approval", () => {
  const dir = mkdtempSync(join(tmpdir(), "plain-loop-test-"));
  approve(dir);
  assert.equal(run(dir, { LAB_DIE_AT: "open_pr:before" }).status, null, "first run is killed by SIGKILL");
  const second = run(dir);
  assert.notEqual(second.status, 0, "second run waits for an approval that never comes and times out");
  const e = events(dir);
  assert.equal(e.filter((x) => x.event === "done" && x.tool === "run_tests").length, 4, "run_tests ran in full twice");
  assert.equal(e.filter((x) => x.event === "approval_requested").length, 2);
});

test("a plain loop with a non-idempotent tool opens a second pull request after a crash", () => {
  const dir = mkdtempSync(join(tmpdir(), "plain-loop-test-"));
  approve(dir);
  run(dir, { LAB_DIE_AT: "open_pr:after", LAB_NO_IDEMPOTENCY: "1" });
  approve(dir);
  assert.equal(run(dir, { LAB_NO_IDEMPOTENCY: "1" }).status, 0);
  assert.equal(JSON.parse(readFileSync(join(dir, "forge.json"), "utf8")).length, 2);
});
