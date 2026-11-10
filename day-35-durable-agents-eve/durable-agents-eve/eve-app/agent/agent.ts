import { defineAgent } from "eve";
import { scriptedModel } from "./lib/scripted-model.ts";

// The lab uses a scripted stand-in so it runs offline with no credentials. For a real agent, replace it with a
// Gateway model id such as "anthropic/claude-sonnet-4.6" or a provider model (docs: agent-config#set-the-model).
export default defineAgent({
  model: scriptedModel as any,
  modelContextWindowTokens: 100_000,
});
