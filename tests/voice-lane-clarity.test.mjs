import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderVoiceStudio(page, context)");
const end = source.indexOf("\n  function renderVoiceCueSheet", start);
assert.ok(start >= 0 && end > start, "Voice Studio renderer boundary must remain present");

test("Voice Studio lane rail keeps one action per lane without repeated guard chips", () => {
  const renderer = source.slice(start, end);
  assert.match(renderer, /portal-voice-lane-card/);
  assert.match(renderer, /portal-voice-lane-action/);
  assert.doesNotMatch(renderer, /lane\.guarded|<em>\$\{safeText\(t\("lane\.guarded/);
});
