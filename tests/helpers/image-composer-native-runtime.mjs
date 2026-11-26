import assert from "node:assert/strict";
import fs from "node:fs";
import {fileURLToPath} from "node:url";
import {pageMetaSources} from "./chat-page-meta-runtime.mjs";

export async function imageComposerRuntime(sources = pageMetaSources()) {
  let loader = fs.readFileSync(new URL("./chat-page-meta-runtime.mjs", import.meta.url), "utf8");
  const once = (old, next) => {
    assert.equal(loader.split(old).length - 1, 1, "Exact test-only runtime exposure");
    loader = loader.replace(old, () => next);
  };
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",
    "\nconst root=" + JSON.stringify(fileURLToPath(new URL("../../", import.meta.url))) + ";");
  once("supportTicketHeroSection,resolvePage,safeText,withUiText:",
    "supportTicketHeroSection,resolvePage,safeText,normalizeImagePromptComposerSaveReceipt,normalizeImagePromptComposerResult,renderImagePromptComposerSaveReceipt,imagePromptComposerFields,withUiText:");
  return (await import("data:text/javascript;base64," + Buffer.from(loader).toString("base64"))).pageMetaRenderer(sources);
}
