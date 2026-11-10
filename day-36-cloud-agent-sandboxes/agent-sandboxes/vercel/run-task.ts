// The same task as common/run_task.py, written against the TypeScript Provider interface.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExecResult, Provider, SandboxHandle, SandboxSpec } from "./provider.ts";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export interface Task {
  name: string;
  workdir: string;
  repo: { fixture: string; url_env: string; ref: string };
  limits: { timeout_s: number; cpu: number; memory_mb: number };
  network: { mode: "allow-all" | "deny-all" | "allow-list"; allow?: string[] };
  commands: { install: string; coverage: string; diff: string };
  agent_target_files: string[];
}

export interface TaskResult {
  provider: string;
  sandboxId: string;
  coverageBefore: number;
  coverageAfter: number;
  diff: string;
  events: Array<Record<string, unknown>>;
}

export function loadTask(): Task {
  return JSON.parse(readFileSync(join(ROOT, "task", "task.json"), "utf8"));
}

export function specFromTask(task: Task): SandboxSpec {
  const net = task.network;
  return {
    timeoutS: task.limits.timeout_s,
    cpu: task.limits.cpu,
    network: net.mode === "allow-list" ? { mode: "allow-list", allow: net.allow ?? [] } : { mode: net.mode },
    env: {},
    secrets: [],
    workdir: task.workdir,
    labels: { task: task.name },
  };
}

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    if (n === "__pycache__" || n === "coverage.json") return [];
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

function must(r: ExecResult, what: string): ExecResult {
  if (r.exitCode !== 0) throw new Error(`${what} failed with exit code ${r.exitCode}: ${(r.stderr || r.stdout).trim()}`);
  return r;
}

const decode = (b: Uint8Array) => new TextDecoder().decode(b);

/** The scripted agent: writes the one test file the sandbox will verify. It is not a model. */
export function scriptedTestFile(): string {
  return readFileSync(join(ROOT, "task", "expected", "test_generated_stock.py"), "utf8");
}

export async function runTask(provider: Provider, task: Task, spec: SandboxSpec = specFromTask(task)): Promise<TaskResult> {
  const events: Array<Record<string, unknown>> = [];
  const note = (step: string, extra: Record<string, unknown> = {}) => events.push({ step, ...extra });
  const wd = task.workdir;
  const sb: SandboxHandle = await provider.create(spec);
  note("create", { sandbox: sb.id });
  try {
    const url = process.env[task.repo.url_env];
    if (url && sb.checkout) {
      await sb.checkout(url, wd, task.repo.ref);
      note("checkout", { source: "git" });
    } else if (url) {
      must(await sb.exec(`git clone --depth 1 --branch ${task.repo.ref} ${url} ${wd}`), "git clone");
      note("checkout", { source: "git" });
    } else {
      must(await sb.exec(`mkdir -p ${wd}`), "mkdir");
      const base = join(ROOT, task.repo.fixture);
      for (const file of walk(base)) await sb.upload(`${wd}/${relative(base, file)}`, readFileSync(file));
      must(await sb.exec("git init -q . && git add -A && git -c user.email=lab@example.invalid -c user.name=lab commit -q -m initial", { cwd: wd }), "git init");
      note("checkout", { source: "fixture" });
    }
    must(await sb.exec("printf 'cov.py\\ncoverage.json\\n__pycache__/\\n' >> .git/info/exclude", { cwd: wd }), "git exclude");
    await sb.upload(`${wd}/cov.py`, readFileSync(join(ROOT, "task", "tools", "cov.py")));
    note("upload_tools");
    must(await sb.exec(task.commands.install, { cwd: wd }), "install");
    note("install");
    must(await sb.exec(task.commands.coverage, { cwd: wd }), "baseline tests");
    const before = JSON.parse(decode(await sb.download(`${wd}/coverage.json`))).percent as number;
    note("baseline", { coverage: before });
    await sb.upload(`${wd}/${task.agent_target_files[0]}`, Buffer.from(scriptedTestFile()));
    note("agent", { wrote: task.agent_target_files[0] });
    must(await sb.exec(task.commands.coverage, { cwd: wd }), "verification tests");
    const after = JSON.parse(decode(await sb.download(`${wd}/coverage.json`))).percent as number;
    note("verify", { coverage: after });
    const diff = must(await sb.exec(task.commands.diff, { cwd: wd }), "git diff").stdout;
    note("collect", { diffBytes: diff.length });
    return { provider: provider.name, sandboxId: sb.id, coverageBefore: before, coverageAfter: after, diff, events };
  } finally {
    await sb.destroy();
    note("destroy");
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.env.SANDBOX_ALLOW_REAL !== "1") {
    console.log("Real runs create billable sandboxes with the credentials in your environment.\nSet SANDBOX_ALLOW_REAL=1 to confirm. The offline default path is: python run_mock.py");
    process.exit(2);
  }
  const { VercelProvider } = await import("./provider.ts");
  const result = await runTask(new VercelProvider(), loadTask());
  console.log(JSON.stringify({ ...result, diff: undefined, diffPreview: result.diff.split("\n").slice(0, 12) }, null, 2));
}
