import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {ROOT, IDS, CUSTOMER, plain, collectionFields, itemFields, runtime} from "./helpers/media-fixed-feedback-runtime.mjs";

const contract = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/media-fixed-feedback-contract.json"), "utf8"));
const text = (key, locale) => {
  const row = [...contract.errors, ...contract.toasts].find(row => row.key === key);
  assert.ok(row, "Independent Root literal expected row exists"); return row[locale];
};
const vectors = [
  ["media-collection-create", collectionFields({title: "x"}), {}, "validation.collectionTitleLength"],
  ["media-collection-update", collectionFields({description: "x".repeat(6001)}), {}, "validation.descriptionLength"],
  ["media-collection-create", collectionFields({creative_brief: "x".repeat(6001)}), {}, "validation.briefLength"],
  ["media-collection-create", collectionFields({prompt_mode: "invalid"}), {}, "validation.mode"],
  ["media-collection-create", collectionFields({project_id: "invalid"}), {}, "validation.project"],
  ["media-collection-create", collectionFields({rights_note: "x"}), {}, "validation.rightsLength"],
  ["media-collection-create", collectionFields({tags: Array.from({length: 17}, (_, index) => "Tag" + index)}), {}, "validation.tagCount"],
  ["media-item-attach", itemFields({role: "invalid"}), {}, "validation.role"],
  ["media-item-update", itemFields({user_declared_duration_seconds: "1.5"}), {}, "validation.duration"],
  ["media-item-attach", itemFields({asset_id: "invalid"}), {}, "validation.asset"],
  ["media-item-update", itemFields({license_note: "x"}), {}, "validation.licenseLength"],
  ["media-workspace-filter", {q: "x".repeat(101)}, {}, "validation.searchLength"],
  ["media-workspace-filter", {prompt_mode: "invalid"}, {}, "validation.filterMode"],
  ["media-workspace-filter", {state: "invalid"}, {}, "validation.filterState"],
  ["media-audio-filter", {q: "x".repeat(101)}, {}, "validation.audioQueryLength"],
  ["media-collection-update", collectionFields(), {mediaCollectionRevision: 0}, "collection.invalidRevision"],
  ["media-collection-restore-version", {}, {mediaCollectionVersion: 0}, "collection.invalidRestoreVersion"],
  ["media-item-detach", {}, {mediaItemId: "invalid"}, "item.invalid"],
  ["media-audio-operation-handoff", {}, {}, "handoff.unavailable"]
];

const apps = new Map();
for (const locale of ["vi", "en", "zh"]) for (const root of ["/media-workspace", "/audio-hub"]) {
  for (const [action, fields, details, key] of vectors) {
    test(`${locale}/${root}/${action}/${key}: physical local error uses owned copy without HTTP`, async () => {
    const id = locale + root;
    if (!apps.has(id)) apps.set(id, runtime(locale, {root}));
    const app = apps.get(id), before = app.observe().toasts.length;
    const actual = await app.dispatch(action, fields, details);
    assert.equal(actual, text(key, locale), action + "/" + key);
    assert.ok(app.observe().toasts.length >= before || app.observe().toasts.length === 3);
    assert.deepEqual(app.observe().network, [], "Local invalid input never reaches HTTP");
    assert.deepEqual(app.observe().forbidden, []);
    assert.equal(app.binding.exposureCount, 1); assert.equal(app.binding.replacedProductionFunctions, 0);
    assert.equal(app.binding.executedIntegrationBytes - app.binding.physicalIntegrationBytes, app.binding.exposureBytes);
  });
  }
}

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: all35 exact local errors and8 fixed feedback values use complete physical catalogue`, () => {
    const app = runtime(locale);
    for (const row of contract.errors) {
      const error = new Error(row.old), before = Object.getOwnPropertyDescriptors(error);
      assert.equal(app.errorText(error), row[locale], row.key);
      assert.deepEqual(Object.getOwnPropertyDescriptors(error), before, "Error identity/data preserved");
    }
    for (const row of contract.toasts) assert.equal(app.feedback(row.key, row.vi), row[locale], row.key);
    assert.deepEqual(app.observe().network, []); assert.deepEqual(app.observe().forbidden, []);
  });
  test(`${locale}: raw API, unknown, near-match and customer errors are never translated or mutated`, () => {
    const app = runtime(locale), known = contract.errors[0].old;
    const inputs = [
      null, undefined, 0, known, CUSTOMER, {}, {message: CUSTOMER}, new Error(CUSTOMER),
      ...["", " ", known + " ", " " + known, known.toUpperCase(), "__proto__", "constructor"].map(value => new Error(value)),
      ...[0, 200, 401, 403, 422, 500, null, undefined, "422"].map(status => Object.assign(new Error(known), {status})),
      ...[null, false, undefined, {}, {message: known}, {message: CUSTOMER}].map(payload => Object.assign(new Error(known), {payload})),
      Object.assign(Object.create({status: 422}), {message: known}),
      Object.assign(Object.create({payload: null}), {message: known})
    ];
    for (const error of inputs) {
      const before = error && typeof error === "object" ? Object.getOwnPropertyDescriptors(error) : null;
      assert.equal(app.errorText(error), null);
      if (before) assert.deepEqual(Object.getOwnPropertyDescriptors(error), before);
    }
    assert.deepEqual(app.observe().network, []); assert.deepEqual(app.observe().forbidden, []);
  });
  test(`${locale}: missing, empty, key-echo and nonstring translator return the approved Vietnamese fallback`, () => {
    const app = runtime(locale);
    for (const mode of ["missing", "empty", "key", "number"]) {
      app.translation(mode);
      for (const row of contract.errors) assert.equal(app.errorText(new Error(row.old)), row.vi, mode + "/" + row.key);
      for (const row of contract.toasts) assert.equal(app.feedback(row.key, row.vi), row.vi, mode + "/" + row.key);
    }
    app.translation("normal");
    assert.equal(app.feedback("collection.composed", text("collection.composed", "vi")), text("collection.composed", locale));
  });
  test(`${locale}: protected producers retain normalized payloads, bounds, tags, strict favorite and revision semantics`, () => {
    const app = runtime(locale);
    const collection = app.call("mediaCollectionPayload", collectionFields());
    assert.deepEqual(plain(collection), {
      title: CUSTOMER, description: CUSTOMER, creative_brief: CUSTOMER, prompt_mode: "background",
      use_context: "Customer context", tags: ["Keep", "TikTok"], rights_note: "Owned rights", project_id: IDS[2]
    });
    const item = app.call("mediaItemPayload", itemFields({favorite: "true", user_declared_duration_seconds: ""}), true);
    assert.deepEqual(plain(item), {role: "music", title_override: CUSTOMER, attribution: CUSTOMER,
      license_note: "Owned rights", tags: ["Keep", "TikTok"], favorite: false, user_declared_duration_seconds: null, asset_id: IDS[1]});
    assert.equal(app.call("mediaWorkspaceLine", "  A \n B  ", "CUSTOMER LABEL", 1, 10, false), "A B");
    assert.equal(app.call("mediaWorkspaceContent", " A\r\nB\rC ", "CUSTOMER LABEL", 10), "A\nB\nC");
    assert.deepEqual(plain(app.call("mediaWorkspaceTags", ["Keep", " keep ", "TikTok"], "CUSTOMER LABEL")), ["Keep", "TikTok"]);
    assert.throws(() => app.call("mediaWorkspaceLine", "long", "CUSTOMER LABEL", 1, 3, false),
      {message: "CUSTOMER LABEL cần từ 1 đến 3 ký tự hợp lệ."});
    assert.throws(() => app.call("mediaWorkspaceContent", "long", "CUSTOMER LABEL", 3),
      {message: "CUSTOMER LABEL tối đa 3 ký tự hợp lệ."});
    assert.throws(() => app.call("mediaCollectionPayload", collectionFields({title: "x"})),
      {message: "Tên collection cần từ 3 đến 180 ký tự hợp lệ."});
    assert.throws(() => app.call("mediaItemPayload", itemFields({user_declared_duration_seconds: "7201"}), true),
      {message: "Thời lượng tự khai báo phải là số nguyên từ 1 đến 7.200 giây."});
    for (const value of [-1, 10001, "invalid"]) assert.equal(app.call("mediaWorkspaceListOffset", value), 0);
    assert.equal(app.call("mediaWorkspaceListOffset", "50"), 50);
    assert.deepEqual(app.observe().network, []); assert.deepEqual(app.observe().forbidden, []);
  });
}
