import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf("  const MUSIC_DIRECTION_PRESETS");
const end = portal.indexOf("  // SFX Cue Sheet is", start);
assert.ok(start >= 0 && end > start, "Music Direction source boundary exists");
const source = portal.slice(start, end);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("Music Direction catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("musicDirectionUi.")).sort());
  assert.ok(keysets[0].length >= 50, "Music Direction catalogue must cover form, preset cards, receipt and boundary");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Music Direction renderer uses locale helper and keeps contracts", () => {
  assert.match(source, /function musicDirectionUiText\(key, fallback, params\)/);
  assert.match(source, /function musicDirectionPresetText\(preset, field\)/);
  assert.ok((source.match(/musicDirectionUiText\(/g) || []).length >= 30);
  for (const stale of [
    "Web-native music planning", "Step 1 · chọn preset", "Lập Music Directions",
    "Review receipt", "Direction receipt · session only", "Use case", "Prompt text", "Execution boundary",
    "Bot callback / keyword", "Provider / AI music", "Lyrics / audio / preview", "Output / job / payment",
    "Asset / collection / delivery", "Scope rõ ràng", "signed session", "direction text"
  ]) {
    assert.doesNotMatch(source, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `fixed mixed copy remains: ${stale}`);
  }
  for (const contract of [
    'data-portal-action="music-direction-preset-compose"',
    'data-portal-route="/media-workspace/music-directions"',
    'name="web_preset_id"', 'name: "description"', 'name: "language"',
    'data-music-direction-submit', 'data-music-direction-preset-card='
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `contract changed: ${contract}`);
});
