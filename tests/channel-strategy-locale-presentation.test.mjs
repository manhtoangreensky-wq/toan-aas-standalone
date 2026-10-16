import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf("  // Channel Strategy takes");
const end = portal.indexOf("  // Music Prompt Composer", start);
assert.ok(start >= 0 && end > start, "Channel Strategy source boundary exists");
const source = portal.slice(start, end);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("Channel Strategy catalogue is balanced and covers renderer chrome", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("channelStrategyUi.")).sort());
  assert.ok(keysets[0].length >= 100, "Channel Strategy catalogue must cover list, detail, fields and preview");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
  for (const key of [
    "channelStrategyUi.guard.title",
    "channelStrategyUi.intro.title",
    "channelStrategyUi.filter.search",
    "channelStrategyUi.field.english",
    "channelStrategyUi.detail.editorTitle",
    "channelStrategyUi.detail.historyTitle",
    "channelStrategyUi.preview.pillars"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], `missing locale key: ${key}`);
  }
});

test("Channel Strategy renderer uses locale helper and preserves workflow contracts", () => {
  assert.match(source, /function channelStrategyText\(key, fallback, params\)/);
  assert.ok((source.match(/channelStrategyText\(/g) || []).length >= 45, "renderer must consume the reviewed catalogue");
  for (const stale of [
    "Execution boundary", "Professional channel operating system", "New channel profile", "Private profile library",
    "Private strategy profile", "Deterministic review direction", "Content pillar", "Cadence direction",
    "Profile editor", "Positioning & guardrail", "Profile lifecycle", "Version history", "Activity", "Snapshot",
    "owner check", "browser storage", "signed account", "optimistic revision", "social lookup", "analytics report"
  ]) {
    assert.doesNotMatch(source, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `fixed English remains: ${stale}`);
  }
  for (const contract of [
    'data-portal-action="channel-strategy-create"',
    'data-portal-action="channel-strategy-filter"',
    'data-portal-action="channel-strategy-refresh"',
    'data-portal-action="channel-strategy-page"',
    'data-portal-action="channel-strategy-update"',
    'data-portal-action="channel-strategy-archive"',
    'data-portal-action="channel-strategy-restore"',
    'data-portal-action="channel-strategy-preview"',
    'name: "channel_name"', 'name: "platform"', 'name: "target_audience"',
    'name: "preferred_aspect_ratio"', 'name: "primary_goal"', 'name="expected_revision"',
    'data-channel-strategy-offset='
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `contract changed: ${contract}`);
});
// End of source locale contract tests.
void 0;
const channelStrategyLocaleContract = true;
