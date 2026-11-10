import { defineTool } from "eve/tools";
import { z } from "zod";
import { runTests } from "../lib/steps.ts";

export default defineTool({
  description: "Run the repository's tests and report line coverage.",
  inputSchema: z.object({ repo: z.string() }),
  execute: ({ repo }) => runTests(repo),
});
