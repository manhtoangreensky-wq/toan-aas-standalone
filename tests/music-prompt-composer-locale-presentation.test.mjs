import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf("  const MUSIC_PROMPT_COMPOSER_MODE_OPTIONS");
const end = portal.indexOf("  // Music Directions deliberately", start);
assert.ok(start >= 0 && end > start, "Music Prompt Composer source boundary exists");
const source = portal.slice(start, end);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("Music Prompt Composer catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("musicPromptComposerUi.")).sort());
  assert.ok(keysets[0].length >= 45, "Music Prompt Composer catalogue must cover page, form, result and boundary chrome");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Music Prompt Composer fixed chrome uses locale helper and keeps contracts", () => {
  assert.match(source, /function musicPromptComposerUiText\(key, fallback, params\)/);
  assert.ok((source.match(/musicPromptComposerUiText\(/g) || []).length >= 30);
  for (const stale of [
    "Web-native deterministic music direction", "Reviewable music direction receipt", "Direction brief",
    "Execution boundary", "Audio source / player", "AI music / lyrics", "Preview / output",
    "Job / wallet / payment", "Asset / collection / delivery", "Telegram action", "Music directions",
    "Usage notes", "Three review directions", "Use case", "Copy-friendly prompt", "Selected direction handoff",
    "Memory Center riêng tư", "owner-only", "browser"
  ]) {
    assert.doesNotMatch(source, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `fixed English remains: ${stale}`);
  }
  for (const contract of [
    'data-portal-action="music-prompt-compose"',
    'data-portal-action="music-prompt-composer-save-memory"',
    'data-portal-route="/media-workspace/music-prompt-composer"',
    'name: "description"', 'name: "mode"', 'name: "language"',
    'name: "suggestion_set"', 'name: "selected_suggestion"'
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `contract changed: ${contract}`);
});
