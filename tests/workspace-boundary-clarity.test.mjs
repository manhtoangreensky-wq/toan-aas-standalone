import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");

test("Document, Analytics and Subtitle workspace boundaries use one explanation", () => {
  for (const [className, oldLabel] of [
    ["portal-document-workspace-guard-list", "OCR / translation"],
    ["portal-analytics-guard-list", "Platform / live API"],
    ["portal-subtitle-studio-guard-list", "ASR / transcription"]
  ]) {
    const start = source.indexOf(`class=\"${className}\"`);
    assert.ok(start >= 0, `${className} remains a styling hook`);
    const end = source.indexOf("</div>", start);
    const snippet = source.slice(start, end);
    assert.match(snippet, /portal-form-note/);
    assert.doesNotMatch(snippet, new RegExp(oldLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});
