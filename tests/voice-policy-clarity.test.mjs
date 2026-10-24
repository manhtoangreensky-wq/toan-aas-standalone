import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderVoiceStudioPolicy(context)");
const end = source.indexOf("\n  function renderVoiceVaultCards", start);
assert.ok(start >= 0 && end > start, "Voice policy renderer boundary must remain present");

test("Voice Studio policy uses one capability explanation instead of four repeated boxes", () => {
  const renderer = source.slice(start, end);
  assert.match(renderer, /portal-voice-studio-guard-list/);
  assert.match(renderer, /portal-voice-studio-guard-summary/);
  assert.doesNotMatch(renderer, /guardItems\.map/);
  assert.match(renderer, /policy\.runtimeGuarded/);
});
