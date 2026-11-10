// A deterministic stand-in for a model (NOT a model). It is a pure function of the prompt it is given, so it behaves
// the same after a crash: it never keeps a counter in memory. Spec: AI SDK LanguageModelV4 (ai ^7).
import { appendFileSync } from "node:fs";
import { join } from "node:path";
import { labDir } from "./lab.ts";

type Decision = { tool: string; input: Record<string, string> } | { text: string };

const PLANS: Record<string, string[]> = {
  full: ["run_tests", "write_test_file", "run_tests", "git_commit", "open_pr"],
  ci: ["ci_gate"],
};

const isError = (o: any) => typeof o?.type === "string" && o.type.startsWith("error");
// What eve puts in the history for a call whose step was interrupted (verified live on eve 1.0.0-rc.5).
const isInterrupted = (o: any) => o?.type === "text" && /may or may not have taken effect/.test(String(o.value));

/**
 * A "model" that follows the plan, and that repeats a call whose result says "may or may not have taken effect".
 * That is what an agent told to make sure the pull request exists tends to do; a careful model would check first.
 */
export function decide(prompt: any[]): Decision {
  const text = JSON.stringify(prompt.filter((m) => m.role === "user"));
  const repo = /repo=([\w.-]+)/.exec(text)?.[1] ?? "repo";
  const order = PLANS[/plan=(\w+)/.exec(text)?.[1] ?? "full"] ?? PLANS.full!;
  const done: string[] = [];
  for (const m of prompt) {
    if (m.role !== "tool") continue;
    for (const part of m.content ?? []) {
      if (part.type !== "tool-result") continue;
      if (isError(part.output)) return { text: `FAILED ${repo}: ${part.toolName} returned an error` };
      if (!isInterrupted(part.output)) done.push(part.toolName);
    }
  }
  if (done.length >= order.length) return { text: `finished ${repo}: ${done.length} steps done` };
  const tool = order[done.length]!;
  return { tool, input: tool === "open_pr" ? { repo, branch: `agent/coverage-${repo}` } : { repo } };
}

const usage = {
  inputTokens: { total: 100, noCache: 100, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: 20, text: 20, reasoning: 0 },
};

function parts(prompt: any[], id: string) {
  if (process.env.LAB_DEBUG_PROMPTS) appendFileSync(join(labDir(), "prompts.jsonl"), JSON.stringify(prompt) + "\n");
  const d = decide(prompt);
  return "tool" in d
    ? [{ type: "tool-call", toolCallId: id, toolName: d.tool, input: JSON.stringify(d.input) }]
    : [{ type: "text", text: d.text }];
}

export const scriptedModel = {
  specificationVersion: "v4" as const,
  provider: "lab",
  modelId: "scripted-coverage-agent",
  supportedUrls: {},
  async doGenerate(options: any) {
    const content = parts(options.prompt, `call-${options.prompt.length}`);
    const calls = content[0]!.type === "tool-call";
    return {
      content,
      finishReason: { unified: calls ? "tool-calls" : "stop", raw: undefined },
      usage,
      warnings: [],
    } as any;
  },
  async doStream(options: any) {
    const content: any[] = parts(options.prompt, `call-${options.prompt.length}`);
    const calls = content[0].type === "tool-call";
    const chunks: any[] = [{ type: "stream-start", warnings: [] }];
    if (calls) chunks.push(content[0]);
    else chunks.push({ type: "text-start", id: "t1" }, { type: "text-delta", id: "t1", delta: content[0].text }, { type: "text-end", id: "t1" });
    chunks.push({ type: "finish", usage, finishReason: { unified: calls ? "tool-calls" : "stop", raw: undefined } });
    return { stream: new ReadableStream({ start(c) { for (const ch of chunks) c.enqueue(ch); c.close(); } }) } as any;
  },
};
