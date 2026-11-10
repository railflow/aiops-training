import { defineTool } from "eve/tools";
import { always } from "eve/tools/approval";
import { z } from "zod";
import { openPr } from "../lib/steps.ts";

export default defineTool({
  description: "Open a pull request for the committed tests. A person must approve each call.",
  inputSchema: z.object({ repo: z.string(), branch: z.string() }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Open a pull request for ${input.repo} from ${input.branch}?`,
  },
  // Approval is consent, not deduplication: the stable key inside openPr is what makes a repeat call harmless.
  execute: ({ repo }) => openPr(repo),
});
