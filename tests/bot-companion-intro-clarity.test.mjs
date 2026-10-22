import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const companionStart = source.indexOf("  function renderBotCompanion(");
const companionEnd = source.indexOf("\n  const ANALYTICS_BOT_COMMAND_PATTERN", companionStart);
const analyticsStart = source.indexOf("  function renderAnalyticsBotCompanion(");
const analyticsEnd = source.indexOf("\n  const CAMPAIGN_PLAN_STATUSES", analyticsStart);
assert.ok(companionStart >= 0 && companionEnd > companionStart, "Bot companion boundary must remain present");
assert.ok(analyticsStart >= 0 && analyticsEnd > analyticsStart, "Analytics companion boundary must remain present");

test("Bot companion intro keeps the action message without technical chips", () => {
  for (const renderer of [source.slice(companionStart, companionEnd), source.slice(analyticsStart, analyticsEnd)]) {
    assert.doesNotMatch(renderer, /portal-state-meta/);
  }
});
