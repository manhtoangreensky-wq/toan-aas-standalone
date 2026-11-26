import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

export function imageComposerReceiptIntegration(source = fs.readFileSync(new URL("../../static/portal/integration.js", import.meta.url), "utf8").replace(/\r\n/g, "\n")) {
  const parts = [];
  for (const name of ["IMAGE_PROMPT_COMPOSER_MEMORY_SAVE_FALSE_BOUNDARY_FIELDS", "IMAGE_PROMPT_COMPOSER_MEMORY_SAVE_RESPONSE_KEYS", "IMAGE_PROMPT_COMPOSER_MEMORY_NOTE_KEYS"]) {
    const start = source.indexOf("  const " + name + " = "), end = source.indexOf(";", start);
    assert(start >= 0 && end > start);
    parts.push(source.slice(start, end + 1));
  }
  for (const name of ["validProjectId", "validMemoryId", "imagePromptComposerVariantIndex", "imagePromptComposerMemorySaveReceipt"]) {
    const start = source.indexOf("  function " + name + "("), end = source.indexOf("\n  }", start);
    assert(start >= 0 && end > start);
    parts.push(source.slice(start, end + 4));
  }
  const box = vm.createContext({});
  vm.runInContext(parts.join("\n") + "\nthis.acceptReceipt=imagePromptComposerMemorySaveReceipt;", box);
  return raw => {
    const snapshot = structuredClone(raw), result = box.acceptReceipt(raw);
    assert.deepEqual(raw, snapshot);
    return JSON.parse(JSON.stringify(result));
  };
}
