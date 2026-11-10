import { defineWorkflowTool } from "eve/tools";
import { RetryableError, sleep } from "eve/workflow";
import { z } from "zod";
import { countEvents, ledger } from "../lib/lab.ts";

// A workflow tool: the body replays, so side effects live in "use step" functions and the wait is a durable `sleep`.
export default defineWorkflowTool({
  description: "Ask CI for the build status, wait for it to settle, then read the final status.",
  inputSchema: z.object({ repo: z.string() }),
  async execute({ repo }) {
    "use workflow";
    const first = await queryCi(repo);
    await sleep(process.env.LAB_SLEEP ?? "10s");
    const final = await readFinalStatus(repo);
    return { repo, first, final };
  },
});

async function queryCi(repo: string) {
  "use step";
  const attempt = countEvents("ci_query_attempt", repo) + 1;
  ledger({ event: "ci_query_attempt", repo, attempt });
  if (attempt <= 2) throw new RetryableError(`CI answered 429 (attempt ${attempt})`, { retryAfter: "1s" });
  return { status: "running", attempt };
}
queryCi.maxRetries = 5;

async function readFinalStatus(repo: string) {
  "use step";
  ledger({ event: "ci_final_read", repo });
  return { status: "passed" };
}
