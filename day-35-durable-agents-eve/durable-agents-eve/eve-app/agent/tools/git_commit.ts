import { defineTool } from "eve/tools";
import { z } from "zod";
import { gitCommit } from "../lib/steps.ts";

export default defineTool({
  description: "Commit the generated tests on a branch.",
  inputSchema: z.object({ repo: z.string() }),
  execute: ({ repo }) => gitCommit(repo),
});
