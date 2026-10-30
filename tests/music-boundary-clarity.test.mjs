import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");

test("Music and SFX authoring boundaries use one capability explanation", () => {
  for (const [className, summaryKey] of [
    ["portal-music-prompt-composer-guard-list", "musicPromptComposerUiText(\"boundary.summary\""],
    ["portal-music-directions-guard-list", "musicDirectionUiText(\"boundary.summary\""],
    ["portal-sfx-cue-sheet-guard-list", "sfxCueSheetUiText(\"boundary.summary\""]
  ]) {
    const start = source.indexOf(`class=\"${className}\"`);
    assert.ok(start >= 0, `${className} remains a styling hook`);
    const end = source.indexOf("</aside>", start);
    const snippet = source.slice(start, end);
    assert.match(snippet, /portal-form-note/);
    assert.match(snippet, new RegExp(summaryKey.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.doesNotMatch(snippet, /<span><strong>/);
  }
});
