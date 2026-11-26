import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {imageComposerReceiptIntegration} from "./helpers/image-composer-receipt-integration.mjs";

const root = new URL("../", import.meta.url);
const source = fs.readFileSync(new URL("static/portal/integration.js", root), "utf8").replace(/\r\n/g, "\n");
const i18nSource = fs.readFileSync(new URL("static/portal/portal-i18n.js", root), "utf8");
const fixture = JSON.parse(fs.readFileSync(new URL("tests/fixtures/image-composer-native-text-results.json", root), "utf8"));
const copy = JSON.parse(fs.readFileSync(new URL("tests/fixtures/image-composer-feedback-copy.json", root), "utf8")).rows;
const start = source.indexOf('      if (action === "image-prompt-composer-select-variant") {');
const end = source.indexOf('      if (action === "image-studio-filter") {', start);
assert(start >= 0 && end > start);
const actions = source.slice(start, end);
const fn = name => {
  const a = source.indexOf("  function " + name + "("), b = source.indexOf("\n  }", a);
  assert(a >= 0 && b > a, name);
  return source.slice(a, b + 4);
};
const functions = ["imageComposerFeedbackText", "imagePromptComposerVariantIndex", "imagePromptComposerResultIsSafe",
  "imagePromptComposerMemorySaveSource", "imagePromptComposerMemorySaveSourceMatchesResult"].map(fn).join("\n");
const declarations = ["IMAGE_PROMPT_COMPOSER_GOALS", "IMAGE_PROMPT_COMPOSER_RATIOS", "IMAGE_PROMPT_COMPOSER_LANGUAGES", "IMAGE_PROMPT_COMPOSER_STYLE_PRESETS"].map(name => {
  const a = source.indexOf("  const " + name + " = "), b = source.indexOf(";", a);
  assert(a >= 0 && b > a); return source.slice(a, b + 1);
}).join("\n");
const acceptReceipt = imageComposerReceiptIntegration();
const flags = ["browser_result_persisted", "pending_bot_save_created", "telegram_state_changed", "bot_called", "bridge_called", "source_image_inspected",
  "provider_called", "image_created", "output_created", "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created", "delivery_created", "fact_checked", "rights_verified"];
const receipt = {...Object.fromEntries(flags.map(key => [key, false])),
  note: {id: "11111111-1111-4111-8111-111111111111", revision: 2, state: "active", category: "Image Prompt Composer", priority: "normal"},
  destination: "memory_note", selected_variant_index: 2, execution: "web_native_memory_note_server_recomputed", draft_recomputed_on_server: true, web_note_persisted: true};
const clone = value => JSON.parse(JSON.stringify(value));
function harness(locale, key) {
  const row = fixture.rows[0], logs = [], requests = [];
  const noop = () => {};
  const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}}, body: {setAttribute: noop}};
  const window = {document, navigator: {language: locale}, location: {pathname: "/image/prompt-composer", search: ""},
    addEventListener: noop, dispatchEvent: noop, localStorage: {getItem: () => null, setItem: noop}};
  let state = {capabilities: {"image-prompt-compose": true, "image-prompt-composer-save-memory": true},
    imagePromptComposerResult: clone(row.result), imagePromptComposerSaveSource: clone(row.source),
    imagePromptComposerSelectedVariantIndex: 2, imagePromptComposerSaveReceipt: clone(receipt)};
  if (["chooseUnavailable", "saveUnavailable"].includes(key)) state.capabilities["image-prompt-compose"] = false;
  if (key === "saveStaleSource") state.imagePromptComposerSaveSource = {};
  if (key === "saveInvalidSelection") state.imagePromptComposerSelectedVariantIndex = 4;
  const box = vm.createContext({window, document, navigator: window.navigator, URL, URLSearchParams, Intl,
    base: () => state,
    merge: patch => {state = {...state, ...clone(patch)}; logs.push({kind: "merge", keys: Object.keys(patch)});},
    toast: (message, type) => logs.push({kind: "toast", message, type: type || "success"}),
    setActionBusy: (_action, _route, busy) => logs.push({kind: "busy", busy}),
    // This test owns fixed-message branches, not request sanitization. The
    // actual matching/shape/boundary and receipt functions are executed below.
    imagePromptComposerPayload: fields => clone(fields), imagePromptComposerSafetyError: () => "",
    imagePromptComposerMemorySaveReceipt: acceptReceipt,
    acquireSubmission: () => key === "saveBusy" ? null : {key: "qa-retry-key"},
    releaseSubmission: () => logs.push({kind: "release"}), discardSubmission: () => logs.push({kind: "discard"}),
    api: async (url, options) => {
      requests.push({url, options: clone(options)});
      if (url.endsWith("/save")) {
        if (key === "saveNotCompleted") return {status: "draft", data: clone(receipt), message: "UNREVIEWED SERVER MESSAGE"};
        return {status: "completed", data: {...clone(receipt), ...(key === "saveInvalidReceipt" ? {provider_called: true} : {}),
          ...(key === "saveMismatchedSelection" ? {selected_variant_index: 1} : {})}, message: "UNREVIEWED SERVER MESSAGE"};
      }
      const data = clone(row.result);
      if (key === "composeInvalidResult") data.provider_called = true;
      if (key === "composeStaleSource") data.composer.subject = "Changed result subject";
      return {data, message: "UNREVIEWED SERVER MESSAGE"};
    }});
  vm.runInContext(i18nSource, box); window.TOANAASI18n.setLocale(locale, {emit: false});
  vm.runInContext(declarations + "\n" + functions + "\nthis.run=async function(action,fields,route){\n" + actions + "\n};", box);
  let action, fields;
  if (key.startsWith("choose") || key.startsWith("selected")) {
    action = "image-prompt-composer-select-variant";
    fields = {__imagePromptComposerSelectedVariantIndex: key === "chooseStale" ? "4" : key === "selectedOriginal" ? "0" : "2"};
  } else if (key.startsWith("compose")) {action = "image-prompt-compose"; fields = clone(row.source);}
  else {action = "image-prompt-composer-save-memory"; fields = {};}
  return {run: () => box.run(action, fields, "/image/prompt-composer"), logs, requests, getState: () => state};
}
const throws = new Set(["chooseUnavailable", "chooseStale", "composeInvalidResult", "composeStaleSource", "saveUnavailable", "saveStaleSource",
  "saveInvalidSelection", "saveNotCompleted", "saveInvalidReceipt", "saveMismatchedSelection"]);
for (const locale of ["vi", "en", "zh"]) for (const row of copy) {
  test(`${locale}: actual Composer action gives truthful native ${row.key} feedback`, async () => {
    const h = harness(locale, row.key), expected = row[locale].replace("{number}", "2");
    if (throws.has(row.key)) await assert.rejects(h.run(), {message: expected});
    else {
      await h.run();
      const toast = h.logs.find(item => item.kind === "toast");
      assert.equal(toast?.message, expected); assert.equal(toast.type, row.key === "saveBusy" ? "error" : "success");
    }
    assert(!h.logs.some(item => item.message === "UNREVIEWED SERVER MESSAGE"));
    if (row.key.startsWith("compose") || ["saveNotCompleted", "saveInvalidReceipt", "saveMismatchedSelection", "saveSuccess"].includes(row.key)) {
      assert.equal(h.requests.length, 1);
      assert.deepEqual(h.logs.filter(item => item.kind === "busy").map(item => item.busy), [true, false]);
    } else assert.equal(h.requests.length, 0);
    if (row.key === "saveSuccess") {
      assert(h.getState().imagePromptComposerSaveReceipt.note);
      const body = JSON.parse(h.requests[0].options.body);
      assert.equal(body.selected_variant_index, 2); assert.equal(body.idempotency_key, "qa-retry-key");
      assert(!Object.hasOwn(body, "composer")); assert(!Object.hasOwn(body, "content"));
      assert.equal(h.logs.filter(item => item.kind === "release").length, 1);
      assert.equal(h.logs.filter(item => item.kind === "discard").length, 1);
    }
    if (row.key === "selectedOriginal" || row.key === "selectedVariant") {
      assert.equal(h.getState().imagePromptComposerSelectedVariantIndex, row.key === "selectedOriginal" ? 0 : 2);
      assert.deepEqual(h.getState().imagePromptComposerSaveReceipt, {});
    }
  });
}
