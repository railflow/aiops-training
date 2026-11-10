import { defineTool } from "eve/tools";
import { z } from "zod";
import { writeTestFile } from "../lib/steps.ts";

export default defineTool({
  description: "Write one generated test file for the least-covered code.",
  inputSchema: z.object({ repo: z.string() }),
  execute: ({ repo }) => writeTestFile(repo),
});
