import assert from "node:assert/strict";
import { test } from "node:test";
import { loadTask, runTask, specFromTask } from "../run-task.ts";
import { toNetworkPolicy, type ExecResult, type Provider, type SandboxHandle, type SandboxSpec } from "../provider.ts";

class RecordingSandbox implements SandboxHandle {
  id = "fake-1";
  calls: string[] = [];
  files = new Map<string, Uint8Array>();
  destroyed = false;
  coverage = [55.2, 98.4];
  async exec(command: string): Promise<ExecResult> {
    this.calls.push(`exec ${command.split(" ")[0]} ${command.includes("cov.py") ? "cov" : ""}`.trim());
    if (command === "python cov.py") {
      this.files.set("/work/repo/coverage.json", Buffer.from(JSON.stringify({ percent: this.coverage.shift() })));
    }
    return { exitCode: 0, stdout: command.includes("git diff") ? "diff --git a/tests/test_generated_stock.py" : "", stderr: "" };
  }
  async upload(path: string, data: Uint8Array) {
    this.calls.push(`upload ${path}`);
    this.files.set(path, data);
  }
  async download(path: string) {
    this.calls.push(`download ${path}`);
    const f = this.files.get(path);
    if (!f) throw new Error("missing " + path);
    return f;
  }
  async destroy() {
    this.destroyed = true;
  }
}

class FakeProvider implements Provider {
  name = "fake";
  sb = new RecordingSandbox();
  specs: SandboxSpec[] = [];
  async create(spec: SandboxSpec) {
    this.specs.push(spec);
    return this.sb;
  }
}

test("the runner performs the documented steps and reports coverage and diff", async () => {
  const p = new FakeProvider();
  const r = await runTask(p, loadTask());
  assert.deepEqual(r.events.map((e) => e.step), ["create", "checkout", "upload_tools", "install", "baseline", "agent", "verify", "collect", "destroy"]);
  assert.equal(r.coverageBefore, 55.2);
  assert.equal(r.coverageAfter, 98.4);
  assert.match(r.diff, /test_generated_stock\.py/);
  assert.ok(p.sb.files.has("/work/repo/tests/test_generated_stock.py"));
});

test("the sandbox is destroyed when a step fails", async () => {
  const p = new FakeProvider();
  p.sb.exec = async () => ({ exitCode: 1, stdout: "", stderr: "boom" });
  await assert.rejects(runTask(p, loadTask()), /failed with exit code 1/);
  assert.equal(p.sb.destroyed, true);
});

test("the task's network policy reaches the provider", async () => {
  const p = new FakeProvider();
  await runTask(p, loadTask());
  assert.equal(p.specs[0].network.mode, "allow-list");
});

test("toNetworkPolicy maps modes and keeps secret values out of the spec", () => {
  const base = specFromTask(loadTask());
  assert.equal(toNetworkPolicy({ ...base, network: { mode: "deny-all" } }), "deny-all");
  assert.equal(toNetworkPolicy({ ...base, network: { mode: "allow-all" } }), "allow-all");
  const spec: SandboxSpec = {
    ...base,
    network: { mode: "allow-list", allow: ["pypi.org", "api.github.com"] },
    secrets: [{ envName: "GITHUB_TOKEN", secretName: "ORCH_GITHUB_TOKEN", hosts: ["api.github.com"] }],
  };
  assert.throws(() => toNetworkPolicy(spec, {}), /not set in the orchestrator environment/);
  const policy = toNetworkPolicy(spec, { ORCH_GITHUB_TOKEN: "value-from-orchestrator" }) as { allow: Record<string, unknown[]> };
  assert.deepEqual(policy.allow["pypi.org"], []);
  assert.deepEqual(policy.allow["api.github.com"], [{ transform: [{ headers: { Authorization: "Bearer value-from-orchestrator" } }] }]);
  assert.ok(!JSON.stringify(spec).includes("value-from-orchestrator"), "the spec holds names, not values");
});
