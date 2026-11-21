import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {ROOT, IDS, CUSTOMER, collectionFields, itemFields, runtime} from "./helpers/media-fixed-feedback-runtime.mjs";

const contract = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/media-fixed-feedback-contract.json"), "utf8"));
const wanted = (key, locale) => contract.toasts.find(row => row.key === key)[locale];
const asset = Object.freeze({id: IDS[1], display_name: "CUSTOMER.wav", original_filename: "CUSTOMER.wav",
  extension: ".wav", content_type: "audio/wav", byte_size: 44, state: "active",
  created_at: "2026-11-21T08:00:00Z", updated_at: "2026-11-21T08:00:00Z",
  archived_at: null, project_id: null, download_available: true});
const collection = Object.freeze({id: IDS[0], title: CUSTOMER, state: "active", revision: 7});
const attached = Object.freeze({id: IDS[2], asset_id: IDS[1], delivery: "asset_vault_attachment_only", asset});
const detail = Object.freeze({collection, items: [attached], versions: [{revision: 7}],
  item_count: 1, item_limit: 250});
const specs = [
  {key: "collection.created", action: "media-collection-create", fields: collectionFields(), method: "POST", target: "/media-workspace/collections", reads: 4},
  {key: "collection.saved", action: "media-collection-update", fields: collectionFields(), method: "PATCH", target: `/media-workspace/collections/${IDS[0]}`, reads: 7},
  {key: "collection.updated", action: "media-collection-archive", fields: {}, method: "POST", target: `/media-workspace/collections/${IDS[0]}/archive`, reads: 7},
  {key: "collection.composed", action: "media-collection-compose", fields: {}, method: "POST", target: `/media-workspace/collections/${IDS[0]}/compose`, reads: 0},
  {key: "item.updated", action: "media-item-attach", fields: itemFields(), method: "POST", target: `/media-workspace/collections/${IDS[0]}/items`, reads: 7}
];
function envelope(data = {}, message) {
  return {payload: {ok: true, status: "ready", ...(message === undefined ? {} : {message}), data}};
}
function metadataReply(entry) {
  assert.equal(entry.method, "GET", "Post-write hydration is read-only");
  if (entry.path === `/media-workspace/collections/${IDS[0]}`) return envelope(detail);
  if (entry.path === "/media-workspace/audio-assets") return envelope({items: [asset], has_more: false, next_offset: null});
  if (entry.path === "/media-workspace/collections") return envelope({items: [collection], has_more: false, next_offset: null});
  if (entry.path === "/media-workspace/events") return envelope({items: []});
  if (entry.path === "/media-workspace/summary") return envelope({collections: {total: 1, active: 1, archived: 0}, items: {total: 1}});
  if (entry.path === "/media-workspace/policy") return envelope({status: "clear", policy: [], guarded_capabilities: []});
  throw Error("Unexpected controlled metadata read: " + entry.path);
}
function mutationData(key) {
  if (key === "collection.composed") return {
    collection_id: IDS[0], revision: 7, execution: "local_deterministic_draft_only", provider_called: false,
    charge_started: false, directions: [1, 2, 3].map(number => ({title: CUSTOMER + number, intent: CUSTOMER, prompt: CUSTOMER + number}))
  };
  return {collection: {...collection, id: key === "collection.created" ? IDS[2] : IDS[0]}};
}
function install(app, spec, message, override) {
  app.controlledMetadataHTTP(entry => {
    if (entry.method === "GET") return metadataReply(entry);
    assert.equal(entry.path, spec.target); assert.equal(entry.method, spec.method);
    if (spec.key !== "collection.composed") assert.match(entry.body.idempotency_key, /^[A-Za-z0-9:_-]+$/);
    if (spec.key !== "collection.created") assert.equal(entry.body.expected_revision, 7);
    return override ? override(entry) : envelope(mutationData(spec.key), message);
  });
}
function assertFlow(app, spec, root) {
  const state = app.observe(), writes = state.network.filter(row => row.method !== "GET");
  assert.equal(writes.length, 1); assert.equal(writes[0].path, spec.target); assert.equal(writes[0].method, spec.method);
  assert.equal(state.network.filter(row => row.method === "GET").length, spec.reads);
  assert.equal(state.network[0].method, spec.method, "Mutation precedes hydration");
  assert.deepEqual(state.forbidden, []);
  if (spec.key === "collection.created") assert.deepEqual(state.navigation, [{kind: "assign", value: root + "/" + IDS[2]}]);
  else assert.deepEqual(state.navigation, []);
  if (spec.key === "collection.composed") {
    assert.equal(state.state.mediaComposer.directions.length, 3);
    assert.equal(state.state.mediaComposer.provider_called, false);
    assert.equal(state.state.mediaComposer.charge_started, false);
    assert.equal(state.state.mediaComposer.directions[0].prompt, CUSTOMER + "1");
  }
}
for (const locale of ["vi", "en", "zh"]) for (const root of ["/media-workspace", "/audio-hub"]) {
  for (const spec of specs) {
    test(`${locale}/${root}/${spec.key}: real dispatcher fallback keeps API, hydration, payload and navigation`, async () => {
      const app = runtime(locale, {root}); install(app, spec);
      const actual = await app.dispatch(spec.action, spec.fields);
      assertFlow(app, spec, root);
      assert.equal(actual, wanted(spec.key, locale));
    });
    test(`${locale}/${root}/${spec.key}: truthy server message remains literal and wins fallback`, async () => {
      const app = runtime(locale, {root}); install(app, spec, CUSTOMER);
      const actual = await app.dispatch(spec.action, spec.fields);
      assertFlow(app, spec, root); assert.equal(actual, CUSTOMER);
    });
  }
  test(`${locale}/${root}/collection.busy: a duplicate in-flight create reports waiting and emits no second write`, async () => {
    const app = runtime(locale, {root}), spec = specs[0];
    let resolve, posts = 0;
    app.controlledMetadataHTTP(entry => {
      if (entry.method === "GET") return metadataReply(entry);
      assert.equal(entry.path, spec.target); assert.equal(entry.method, "POST"); posts++;
      return new Promise(yes => { resolve = yes; });
    });
    const first = app.dispatch(spec.action, spec.fields);
    assert.equal(posts, 1);
    const duplicateText = await app.dispatch(spec.action, spec.fields);
    assert.equal(posts, 1);
    resolve(envelope(mutationData(spec.key), CUSTOMER));
    await first; assertFlow(app, spec, root);
    assert.equal(duplicateText, wanted("collection.busy", locale));
  });
  for (const available of [true, false]) {
    const key = available ? "handoff.opened" : "handoff.sourceMissing";
    test(`${locale}/${root}/${key}: fresh source revalidation precedes navigation, selected metadata and focus`, async () => {
      const app = runtime(locale, {root});
      app.controlledMetadataHTTP(entry => {
        assert.equal(entry.method, "GET");
        if (entry.path === `/media-workspace/collections/${IDS[0]}`) return envelope(detail);
        if (entry.path === "/asset-vault") return envelope({items: available ? [asset] : [], has_more: false, next_offset: null});
        if (entry.path === "/audio-asset-operations") return envelope({operations: []});
        throw Error("Unexpected handoff path: " + entry.path);
      }, {mediaCollectionDetail: detail, assetVaultEnabled: true, audioAssetOperationsEnabled: true,
        capabilities: {"audio-asset-operation-view": true}});
      const actual = await app.dispatch("media-audio-operation-handoff");
      const state = app.observe();
      assert.deepEqual(state.network.map(row => row.method), ["GET", "GET", "GET"]);
      assert.equal(state.network[0].path, `/media-workspace/collections/${IDS[0]}`);
      assert.deepEqual(state.navigation, [{kind: "pushState", value: "/audio/assets"}]);
      assert.equal(state.state.path, "/audio/assets");
      assert.equal(state.state.audioAssetReferences.selected?.id ?? null, available ? IDS[1] : null);
      assert.equal(state.focus.length, 1); assert.equal(state.focus[0].id, "audio-asset-source");
      assert.deepEqual(state.forbidden, []);
      assert.equal(state.toasts.at(-1).attributes.role, available ? "status" : "status");
      assert.equal(actual, wanted(key, locale));
    });
  }
}
