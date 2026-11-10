// Tiny "world" for the lab: a ledger of every side effect and a fake forge, both plain files.
// Real tools would call git, a test runner and a forge API; the durability behaviour does not depend on that.
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

/** Read on every call so a test can point each case at its own directory. */
export const labDir = () => {
  const dir = process.env.LAB_DIR ?? join(process.cwd(), ".lab");
  mkdirSync(join(dir, "repos"), { recursive: true });
  return dir;
};

export function ledger(entry: Record<string, unknown>) {
  appendFileSync(join(labDir(), "ledger.jsonl"), JSON.stringify({ pid: process.pid, ...entry }) + "\n");
}

export function countEvents(event: string, repo: string): number {
  const file = join(labDir(), "ledger.jsonl");
  if (!existsSync(file)) return 0;
  return readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)).filter((e) => e.event === event && e.repo === repo).length;
}

export function readRepo(repo: string): { tests: string[]; committed: boolean } {
  const file = join(labDir(), "repos", `${repo}.json`);
  return existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : { tests: [], committed: false };
}

export function writeRepo(repo: string, state: { tests: string[]; committed: boolean }) {
  writeFileSync(join(labDir(), "repos", `${repo}.json`), JSON.stringify(state));
}

export function pullRequests(): { repo: string; key: string }[] {
  const file = join(labDir(), "forge.json");
  return existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : [];
}

export function savePullRequests(prs: { repo: string; key: string }[]) {
  writeFileSync(join(labDir(), "forge.json"), JSON.stringify(prs));
}

export const stepMs = () => Number(process.env.LAB_STEP_MS ?? "0");
export const pause = (ms: number) => (ms > 0 ? sleep(ms) : Promise.resolve());

/** LAB_DIE_AT="tool:before" or "tool:after" kills this process with SIGKILL once (a marker file stops a second death). */
export function maybeDie(tool: string, when: "before" | "after") {
  if (process.env.LAB_DIE_AT !== `${tool}:${when}`) return;
  const marker = join(labDir(), `died-${tool}-${when}`);
  if (existsSync(marker)) return;
  writeFileSync(marker, "x");
  ledger({ event: "KILLED", tool, when });
  process.kill(process.pid, "SIGKILL");
}
