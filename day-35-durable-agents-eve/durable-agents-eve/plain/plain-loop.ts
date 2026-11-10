// The same agent as eve-app, as a plain in-memory loop: the model decides, we run the tool, we append the result, repeat.
// All state lives in this process. It uses the same scripted model and the same tool steps as the eve app.
import { existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { labDir, ledger } from "../eve-app/agent/lib/lab.ts";
import { decide } from "../eve-app/agent/lib/scripted-model.ts";
import { gitCommit, openPr, runTests, writeTestFile } from "../eve-app/agent/lib/steps.ts";

const repo = process.argv[2] ?? "billing-001";
const approvals = join(labDir(), "approvals");
mkdirSync(approvals, { recursive: true });

const tools: Record<string, (r: string) => Promise<unknown>> = {
  run_tests: runTests, write_test_file: writeTestFile, git_commit: gitCommit, open_pr: openPr,
};

// The "approval" is a click that is consumed: the file is deleted once the loop has read it, like a button press.
async function waitForApproval(): Promise<void> {
  const file = join(approvals, repo);
  ledger({ event: "approval_requested", tool: "open_pr", repo });
  const deadline = Date.now() + Number(process.env.LAB_APPROVAL_WAIT_MS ?? "60000");
  while (!existsSync(file)) {
    if (Date.now() > deadline) throw new Error("approval timed out");
    await sleep(100);
  }
  rmSync(file);
  ledger({ event: "approval_consumed", repo });
}

const prompt: any[] = [{ role: "user", content: [{ type: "text", text: `Improve coverage. repo=${repo}` }] }];
for (let i = 0; i < 20; i++) {
  const d = decide(prompt);
  if ("text" in d) { console.log(`plain loop: ${d.text}`); break; }
  if (d.tool === "open_pr") await waitForApproval();
  const result = await tools[d.tool]!(repo);
  prompt.push({ role: "assistant", content: [{ type: "tool-call", toolCallId: `c${i}`, toolName: d.tool, input: d.input }] });
  prompt.push({ role: "tool", content: [{ type: "tool-result", toolCallId: `c${i}`, toolName: d.tool, output: { type: "json", value: result } }] });
}
