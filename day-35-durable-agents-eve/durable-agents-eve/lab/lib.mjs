// Helpers for the crash lab: start and kill -9 an `eve start` server, talk to its HTTP protocol, read the ledger.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
export const APP = join(ROOT, "eve-app");
const EVE_BIN = join(APP, "node_modules", "eve", "bin", "eve.js");

export const say = (msg) => console.log(msg);
export const newLabDir = (name) => mkdtempSync(join(tmpdir(), `eve-lab-${name}-`));

export function ledger(dir) {
  const file = join(dir, "ledger.jsonl");
  return existsSync(file) ? readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)) : [];
}
export const count = (dir, event, tool, repo) =>
  ledger(dir).filter((e) => e.event === event && (!tool || e.tool === tool) && (!repo || e.repo === repo)).length;
export const forge = (dir) => (existsSync(join(dir, "forge.json")) ? JSON.parse(readFileSync(join(dir, "forge.json"), "utf8")) : []);

export function assert(cond, msg) {
  if (!cond) throw new Error(`ASSERTION FAILED: ${msg}`);
  say(`  ok: ${msg}`);
}

export class Server {
  constructor(port, env) {
    this.port = port;
    this.env = env;
    this.base = `http://127.0.0.1:${port}`;
    this.child = null;
  }

  async start() {
    this.child = spawn(process.execPath, [EVE_BIN, "start", "--port", String(this.port)], {
      cwd: APP, env: { ...process.env, ...this.env }, detached: true, stdio: ["ignore", "ignore", "ignore"],
    });
    this.exited = new Promise((resolve) => this.child.once("exit", (code, sig) => resolve({ code, sig })));
    for (let i = 0; i < 100; i++) {
      try { if ((await fetch(`${this.base}/eve/v1/health`)).ok) return; } catch {}
      await sleep(200);
    }
    throw new Error("eve start did not become healthy");
  }

  alive() { return this.child !== null && this.child.exitCode === null && this.child.signalCode === null; }

  kill9() {
    try { process.kill(-this.child.pid, "SIGKILL"); } catch {}
  }

  async waitForDeath(ms = 20000) {
    const t = Date.now();
    while (this.alive() && Date.now() - t < ms) await sleep(100);
    return !this.alive();
  }

  async post(path, body) {
    const res = await fetch(`${this.base}${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
    return res.json();
  }

  async createSession(message) {
    const res = await this.post("/eve/v1/session", { message });
    if (!res.ok) throw new Error(`create failed: ${JSON.stringify(res)}`);
    return res.sessionId;
  }

  async facts(sessionId) {
    const res = await fetch(`${this.base}/eve/v1/session/${sessionId}/stream?follow=false`);
    const out = [];
    for (const line of (await res.text()).split("\n")) {
      if (!line.trim()) continue;
      try { out.push(...(JSON.parse(line).facts ?? [])); } catch {}
    }
    return out;
  }

  async state(sessionId) {
    const facts = await this.facts(sessionId);
    const settled = new Set(facts.filter((f) => f.type === "interaction.settled").map((f) => f.data.interactionId));
    const open = facts.filter((f) => f.type === "interaction.opened" && !settled.has(f.data.interactionId)).map((f) => f.data);
    const reply = facts.filter((f) => f.type === "content.completed" && f.data.phase === "reply").map((f) => f.data.value).at(-1);
    return { facts, open, done: facts.some((f) => f.type === "turn.settled"), reply };
  }

  async approve(sessionId, interactionId, optionId = "approve") {
    return this.post(`/eve/v1/session/${sessionId}`, { answers: [{ interactionId, optionId }] });
  }

  async waitFor(sessionId, predicate, ms = 60000) {
    const t = Date.now();
    for (;;) {
      const s = await this.state(sessionId);
      if (predicate(s)) return s;
      if (Date.now() - t > ms) throw new Error(`timeout waiting on ${sessionId}`);
      await sleep(250);
    }
  }
}

export function resetWorkflowData() {
  rmSync(join(APP, ".eve", ".workflow-data"), { recursive: true, force: true });
}

/**
 * Short durable waits (a `sleep` in a workflow) recorded by the local world. The 30-day session-timeout wait that every
 * session has is ignored, so this is true only once the sleep itself is in flight.
 */
export const registeredSleeps = () => {
  const dir = join(APP, ".eve", ".workflow-data", "waits");
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).map((f) => JSON.parse(readFileSync(join(dir, f), "utf8")))
    .filter((w) => w.status === "waiting" && new Date(w.resumeAt).getTime() - Date.now() < 3600_000).length;
};
