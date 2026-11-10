// Provider interface (the TypeScript twin of common/provider.py) and the Vercel Sandbox implementation.
// Verified against @vercel/sandbox 3.9.1 types; NOT run against a live account (see README).
import { Sandbox, type NetworkPolicy } from "@vercel/sandbox";

export type NetworkSpec =
  | { mode: "allow-all" }
  | { mode: "deny-all" }
  | { mode: "allow-list"; allow: string[] };

export interface SecretRef {
  envName: string;
  /** Name of a variable in the ORCHESTRATOR's environment that holds the value. The value never goes into the sandbox. */
  secretName: string;
  hosts: string[];
  /** Header the firewall sets on requests to `hosts`. */
  header?: string;
}

export interface SandboxSpec {
  timeoutS: number;
  cpu: number;
  network: NetworkSpec;
  env: Record<string, string>;
  secrets: SecretRef[];
  workdir: string;
  labels: Record<string, string>;
}

export interface ExecResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

export interface SandboxHandle {
  id: string;
  exec(command: string, opts?: { cwd?: string; env?: Record<string, string>; timeoutS?: number }): Promise<ExecResult>;
  upload(remotePath: string, data: Uint8Array): Promise<void>;
  download(remotePath: string): Promise<Uint8Array>;
  destroy(): Promise<void>;
  checkout?(url: string, path: string, ref: string): Promise<void>;
}

export interface Provider {
  name: string;
  create(spec: SandboxSpec): Promise<SandboxHandle>;
}

/** Translate the neutral spec into Vercel's firewall rules. Secrets are brokered: the firewall adds the header for allowed hosts. */
export function toNetworkPolicy(spec: SandboxSpec, env: NodeJS.ProcessEnv = process.env): NetworkPolicy {
  if (spec.network.mode === "allow-all") return "allow-all";
  if (spec.network.mode === "deny-all") return "deny-all";
  const rules: Record<string, Array<{ transform: Array<{ headers: Record<string, string> }> }>> = {};
  for (const host of spec.network.allow) rules[host] = [];
  for (const secret of spec.secrets) {
    const value = env[secret.secretName];
    if (!value) throw new Error(`secret ${secret.secretName} is not set in the orchestrator environment`);
    for (const host of secret.hosts) {
      rules[host] = [{ transform: [{ headers: { [secret.header ?? "Authorization"]: `Bearer ${value}` } }] }];
    }
  }
  return { allow: rules };
}

class VercelSandbox implements SandboxHandle {
  id: string;
  private sb: Sandbox;
  constructor(sb: Sandbox) {
    this.sb = sb;
    this.id = sb.name;
  }

  async exec(command: string, opts: { cwd?: string; env?: Record<string, string>; timeoutS?: number } = {}): Promise<ExecResult> {
    const done = await this.sb.runCommand({
      cmd: "bash",
      args: ["-lc", command],
      cwd: opts.cwd,
      env: opts.env,
      timeoutMs: opts.timeoutS ? opts.timeoutS * 1000 : undefined,
    });
    return { exitCode: done.exitCode, stdout: await done.stdout(), stderr: await done.stderr() };
  }

  async upload(remotePath: string, data: Uint8Array): Promise<void> {
    await this.sb.writeFiles([{ path: remotePath, content: Buffer.from(data) }]);
  }

  async download(remotePath: string): Promise<Uint8Array> {
    const buf = await this.sb.readFileToBuffer({ path: remotePath });
    if (buf === null) throw new Error(`no such file in the sandbox: ${remotePath}`);
    return buf;
  }

  async destroy(): Promise<void> {
    await this.sb.stop();
  }
}

export class VercelProvider implements Provider {
  name = "vercel-sandbox";

  async create(spec: SandboxSpec): Promise<SandboxHandle> {
    // Auth comes from VERCEL_OIDC_TOKEN (after `vercel link && vercel env pull`) or from VERCEL_TEAM_ID / VERCEL_PROJECT_ID / VERCEL_TOKEN.
    const sb = await Sandbox.create({
      timeout: spec.timeoutS * 1000,
      resources: { vcpus: spec.cpu <= 1 ? 1 : 2 },
      networkPolicy: toNetworkPolicy(spec),
      env: spec.env,
      tags: spec.labels,
      persistent: false,
    });
    return new VercelSandbox(sb);
  }
}
