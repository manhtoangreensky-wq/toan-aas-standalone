import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {imageComposerRuntime} from "./helpers/image-composer-native-runtime.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/image-composer-native-locale-contract.json", import.meta.url), "utf8"));
const sources = pageMetaSources(), original = {...sources};
for (const [key, file] of [["portal", "static/portal/portal.js"], ["i18n", "static/portal/portal-i18n.js"]]) {
  original[key] = execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
}
const previous = await imageComposerRuntime(original), current = await imageComposerRuntime(sources);
const route = "/image/prompt-composer";
const oldApi = previous("vi", route, {}).qa.normalizeImagePromptComposerSaveReceipt;
const api = current("vi", route, {}).qa.normalizeImagePromptComposerSaveReceipt;
const flags = ["browser_result_persisted", "pending_bot_save_created", "telegram_state_changed",
  "bot_called", "bridge_called", "source_image_inspected", "provider_called", "image_created", "output_created",
  "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created", "delivery_created",
  "fact_checked", "rights_verified"];
const receipt = {...Object.fromEntries(flags.map(key => [key, false])),
  note: {id: "11111111-1111-4111-8111-111111111111", revision: 2, state: "active", category: "Image Prompt Composer", priority: "normal"},
  destination: "memory_note", selected_variant_index: 0, execution: "web_native_memory_note_server_recomputed",
  draft_recomputed_on_server: true, web_note_persisted: true};
const plain = value => JSON.parse(JSON.stringify(value));
const call = (fn, input) => {
  const before = structuredClone(input), value = plain(fn(input));
  assert.deepEqual(input, before, "Normalizer must not mutate input, including undefined fields");
  return value;
};

for (const index of [0, 1, 2, 3]) for (const revision of [1, "2", 1000000]) {
  test(`receipt remains strict and idempotent for selection${index},revision${revision}`, () => {
    const input = {...receipt, note: {...receipt.note, revision}, selected_variant_index: index};
    const old = call(oldApi, input), once = call(api, input), twice = call(api, once);
    assert.deepEqual(call(oldApi, old), {}, "Delivered baseline reproduced its lost receipt");
    assert.deepEqual(twice, once);
    for (const key of ["note", "destination", "selected_variant_index"]) assert.deepEqual(once[key], old[key]);
    assert.deepEqual(Object.keys(once).sort(), Object.keys(input).sort());
    for (const flag of flags) assert.equal(once[flag], false);
    assert.equal(once.execution, receipt.execution);
    assert.equal(once.draft_recomputed_on_server, true);
    assert.equal(once.web_note_persisted, true);
  });
}

const invalid = [];
for (const flag of flags) for (const [index, value] of [true, "false", 0, null, undefined].entries()) {
  invalid.push({name: `${flag}:invalidType${index}`, value: {...receipt, [flag]: value}});
}
for (const key of Object.keys(receipt)) {
  const value = structuredClone(receipt); delete value[key];
  invalid.push({name: `missing:${key}`, value});
}
invalid.push(
  {name: "extra:content", value: {...receipt, content: "MUST_NOT_STORE_OR_RENDER"}},
  {name: "unknown:execution", value: {...receipt, execution: "unknown"}},
  {name: "not:serverRecomputed", value: {...receipt, draft_recomputed_on_server: false}},
  {name: "not:persisted", value: {...receipt, web_note_persisted: false}}
);
for (const [index, value] of [-1, 4, 0.5, "2", true, null].entries()) {
  invalid.push({name: `invalidSelectionType${index}`, value: {...receipt, selected_variant_index: value}});
}
for (const [index, patch] of [{id: "invalid"}, {revision: 0}, {revision: 1.5}, {revision: 1000001},
  {state: "archived"}, {category: "CUSTOMER CATEGORY"}, {priority: "urgent"}, {content: "MUST_NOT_STORE_OR_RENDER"}].entries()) {
  invalid.push({name: `invalidNote${index}`, value: {...receipt, note: {...receipt.note, ...patch}}});
}
assert.equal(invalid.length, 126);
for (const item of invalid) {
  test(`current receipt keeps baseline rejection: ${item.name}`, () => {
    assert.deepEqual(call(oldApi, item.value), {});
    assert.deepEqual(call(api, item.value), {});
  });
}

for (const [localeIndex, locale] of ["vi", "en", "zh"].entries()) for (const index of [0, 1, 2, 3]) {
  test(`${locale}: receipt survives actual bootstrap and second renderer normalization, selection${index}`, () => {
    const raw = {imagePromptComposerEnabled: true, capabilities: {"image-prompt-compose": true},
      imagePromptComposerSaveReceipt: {...receipt, selected_variant_index: index}};
    const before = previous(locale, route, raw), after = current(locale, route, raw);
    assert(before.context.imagePromptComposerSaveReceipt.note);
    assert.equal(before.qa.renderImagePromptComposerSaveReceipt(before.context.imagePromptComposerSaveReceipt), "", "Baseline lost visible saved receipt");
    assert(after.qa.renderImagePromptComposerSaveReceipt(after.context.imagePromptComposerSaveReceipt).includes('href="/notes"'));
    assert(after.html.includes('href="/notes"'));
    for (const key of ["receipt.categoryFallback", "receipt.description", "receipt.open"]) {
      assert(after.html.includes(contract.copyRows.find(row => row[0] === key)[localeIndex + 1]), key);
    }
    assert.equal(after.context.imagePromptComposerSaveReceipt.note.category, "Image Prompt Composer");
    assert(!after.html.includes("MUST_NOT_STORE_OR_RENDER"));
  });
}
