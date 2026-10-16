import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf("  const SFX_CUE_SHEET_ROUTE");
const end = portal.indexOf("  const PROMPT_STUDIO_PLATFORM_OPTIONS", start);
assert.ok(start >= 0 && end > start, "SFX Cue Sheet source boundary exists");
const source = portal.slice(start, end);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("SFX Cue Sheet catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("sfxCueSheetUi.")).sort());
  assert.ok(keysets[0].length >= 55, "SFX catalogue must cover form, presets, receipt and boundary");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("SFX Cue Sheet renderer uses locale helper and preserves contracts", () => {
  assert.match(source, /function sfxCueSheetUiText\(key, fallback, params\)/);
  assert.match(source, /function sfxCueSheetPresetText\(preset, field\)/);
  assert.ok((source.match(/sfxCueSheetUiText\(/g) || []).length >= 30);
  for (const stale of [
    "Web-native editorial SFX planning", "Step 1 · chọn hướng", "Lập SFX Cue Sheet", "Preset SFX Web",
    "Cue sheet receipt", "Cue sheet receipt · session only", "Execution boundary", "Raw Bot callback / keyword",
    "Source video / audio inspect", "Catalog / provider / SFX", "Player / preview / output", "Job / wallet / payment",
    "Asset / collection / delivery", "Scope rõ ràng", "source media inspection", "semantic"
  ]) {
    assert.doesNotMatch(source, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `fixed mixed copy remains: ${stale}`);
  }
  for (const contract of [
    'data-portal-action="sfx-cue-sheet-compose"',
    'data-portal-route="/media-workspace/sfx-cue-sheet"',
    'name="web_sfx_preset_id"', 'name: "description"', 'name: "language"',
    'data-sfx-cue-sheet-submit', 'data-sfx-cue-sheet-preset-card='
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `contract changed: ${contract}`);
});
