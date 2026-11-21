import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {physicalSources, audioRuntime, hash, plain, freeze, asset, IDS, CUSTOMER} from "./helpers/media-audio-read-feedback-runtime.mjs";

// Owner-frozen literal expectations, independent of the application catalog.
const COPY = freeze({
  vi: {
    audioFiltered: "Đã lọc danh sách tệp âm thanh.", audioAll: "Đã hiển thị tất cả tệp âm thanh.",
    audioPage: "Đã tải danh sách tệp âm thanh.", audioReadFailed: "Chưa tải được danh sách tệp âm thanh. Hãy thử lại.",
    audioFilterUnavailable: "Chưa thể tìm tệp âm thanh lúc này.", audioPageUnavailable: "Chưa thể chuyển trang tệp âm thanh lúc này."
  },
  en: {
    audioFiltered: "Audio files filtered.", audioAll: "All audio files shown.",
    audioPage: "Audio file list loaded.", audioReadFailed: "Could not load the audio file list. Try again.",
    audioFilterUnavailable: "Audio file search is not available right now.", audioPageUnavailable: "Audio file pages are not available right now."
  },
  zh: {
    audioFiltered: "音频文件已筛选。", audioAll: "已显示全部音频文件。",
    audioPage: "音频文件列表已加载。", audioReadFailed: "未能加载音频文件列表，请重试。",
    audioFilterUnavailable: "暂时无法搜索音频文件。", audioPageUnavailable: "暂时无法切换音频文件页面。"
  }
});
const ACTIONS = freeze([
  {action: "filter", key: "audioFiltered", fields: {q: "  CUSTOMER   QUERY  "},
    query: {limit: "50", offset: "0", q: "CUSTOMER QUERY"}},
  {action: "clear", key: "audioAll", fields: {q: "IGNORED"},
    query: {limit: "50", offset: "0"}},
  {action: "page", key: "audioPage", fields: {__mediaAudioOffset: 100},
    query: {limit: "50", offset: "100", q: "OLD_AUDIO"}}
]);
const source = physicalSources(), create = (locale = "vi", options = {}) => audioRuntime(locale, {...options, source});
const rowFor = action => ACTIONS.find(row => row.action === action);
const toast = (text, failed = false) => ({
  text, role: failed ? "alert" : "status", className: failed ? "portal-toast portal-toast--warning" : "portal-toast"
});
function safe(runtime, count = 1) {
  const seen = runtime.observe();
  assert.deepEqual(seen.forbidden, [], "No real network/storage/navigation/product writes/HTML");
  assert.equal(seen.network.length, count);
  assert.ok(seen.network.every(row => row.method === "GET"));
  assert.ok(runtime.pending.every(row => row.settled), "All controlled GETs settled");
}
function request(runtime, job, row) {
  assert.equal(job.indices.length, 1, "One real audio reader GET");
  assert.deepEqual(runtime.network[job.indices[0]], {
    path: "/api/v1/media-workspace/audio-assets", method: "GET", query: row.query
  });
}
function listing(q, offset, returned, hasMore = returned > 0, nextOffset = hasMore ? offset + 50 : null) {
  return {filters: {q}, pagination: {limit: 50, offset, returned, has_more: hasMore,
    next_offset: nextOffset, previous_offset: offset >= 50 ? offset - 50 : null}};
}
function unrelated(state) {
  const {mediaAudioAssets: _assets, mediaAudioAssetFilter: _filter, mediaAudioAssetListing: _listing, ...rest} = state;
  return plain(rest);
}

test("binding: complete physical integration+i18n execute with one exposure and no production replacement", t => {
  const runtime = create();
  for (const key of ["integration", "i18n"]) {
    const raw = fs.readFileSync(runtime.binding.paths[key], "utf8");
    assert.equal(source.sources[key], raw);
    assert.equal(runtime.binding.hashes[key], hash(raw));
  }
  assert.equal(runtime.binding.executedIntegrationBytes, runtime.binding.physicalIntegrationBytes + runtime.binding.exposureBytes);
  assert.equal(runtime.binding.exposureCount, 1);
  assert.equal(runtime.binding.replacedProductionFunctions, 0);
  assert.notEqual(runtime.binding.executedIntegrationHash, source.hashes.integration);
  t.diagnostic(JSON.stringify(runtime.binding));
  safe(runtime, 0);
});

// One current-read axis proves both detail visual roots, every action and every
// locale. Separate tables below cover fences/capabilities/races without repeating
// that entire product.
for (const root of ["/media-workspace", "/audio-hub"]) {
  for (const locale of ["vi", "en", "zh"]) {
    for (const row of ACTIONS) {
      for (const outcome of ["nonempty", "empty", "failed"]) {
        test(`${root}/${locale}/${row.action}/${outcome}: current audio outcome owns localized feedback`, async () => {
          const runtime = create(locale, {root}), before = unrelated(runtime.state);
          const job = runtime.start(row.action, row.fields);
          request(runtime, job, row);
          assert.deepEqual(runtime.observe().toasts, [], "No completion feedback before await");
          const failed = outcome === "failed", items = outcome === "nonempty" ? [asset()] : [];
          runtime.settle(job.indices[0], {failed, items});
          await job.work;
          assert.deepEqual(unrelated(runtime.state), before, "Collection detail/global state unchanged");
          assert.deepEqual(plain(runtime.state.mediaAudioAssets), items);
          assert.deepEqual(plain(runtime.state.mediaAudioAssetFilter), {q: row.query.q || ""});
          assert.deepEqual(plain(runtime.state.mediaAudioAssetListing),
            listing(row.query.q || "", Number(row.query.offset), items.length));
          safe(runtime);
          assert.deepEqual(runtime.observe().toasts, [toast(COPY[locale][failed ? "audioReadFailed" : row.key], failed)]);
        });
      }
    }
  }
}

test("empty filter: no query is all-files success, not a nonempty-search announcement", async () => {
  const runtime = create("en"), job = runtime.start("filter", {q: "   "});
  assert.deepEqual(runtime.network[0].query, {limit: "50", offset: "0"});
  runtime.settle(0, {items: []});
  await job.work;
  safe(runtime);
  assert.deepEqual(runtime.observe().toasts, [toast(COPY.en.audioAll)]);
});

// The reader owns audio/session/path/auth/enabled currentness. Collection
// counter changes do not alter that loader contract, but must silence action
// feedback after another collection reader has taken ownership of the screen.
const STALE = [
  ...ACTIONS.flatMap(row => ["audioEpoch", "listEpoch", "detailEpoch"].map(boundary => ({...row, boundary}))),
  {...ACTIONS[0], boundary: "route"}, {...ACTIONS[0], boundary: "session"},
  {...ACTIONS[2], boundary: "logout"}, {...ACTIONS[2], boundary: "disabled"}
];
for (const row of STALE) {
  for (const failed of [false, true]) {
    test(`stale/${row.action}/${row.boundary}/${failed ? "failed" : "ready"}: superseded audio feedback is silent`, async () => {
      const runtime = create("en", {root: "/audio-hub"});
      const job = runtime.start(row.action, row.fields);
      request(runtime, job, row);
      runtime.mutate(row.boundary);
      const before = runtime.observe().state;
      runtime.settle(0, {failed});
      await job.work;
      if (["listEpoch", "detailEpoch"].includes(row.boundary)) {
        assert.deepEqual(unrelated(runtime.state), unrelated(before));
        assert.deepEqual(plain(runtime.state.mediaAudioAssets), failed ? [] : [asset()]);
        assert.deepEqual(plain(runtime.state.mediaAudioAssetListing),
          listing(row.query.q || "", Number(row.query.offset), failed ? 0 : 1));
      } else assert.deepEqual(runtime.observe().state, before, "Stale raw reader does not merge");
      safe(runtime);
      assert.deepEqual(runtime.observe().toasts, [], "No stale success or stale warning");
    });
  }
}

for (const pair of [["filter", "filter"], ["filter", "page"], ["page", "clear"]]) {
  for (const olderFailed of [false, true]) {
    for (const olderFirst of [false, true]) {
      test(`overlap/${pair.join("-")}/old-${olderFailed ? "failed" : "ready"}/${olderFirst ? "old-first" : "new-first"}`, async () => {
        const runtime = create("en");
        const oldRow = rowFor(pair[0]), newRow = rowFor(pair[1]);
        const older = runtime.start(oldRow.action, oldRow.fields);
        const newer = runtime.start(newRow.action, newRow.fields);
        request(runtime, older, oldRow); request(runtime, newer, newRow);
        let firstFeedback, afterNewer;
        if (olderFirst) {
          runtime.settle(older.indices[0], {failed: olderFailed});
          await older.work;
          firstFeedback = runtime.observe().toasts;
          runtime.settle(newer.indices[0], {failed: !olderFailed});
          await newer.work;
        } else {
          runtime.settle(newer.indices[0], {failed: !olderFailed});
          await newer.work;
          afterNewer = runtime.observe();
          runtime.settle(older.indices[0], {failed: olderFailed});
          await older.work;
        }
        assert.deepEqual(plain(runtime.state.mediaAudioAssets), olderFailed ? [asset()] : []);
        assert.deepEqual(plain(runtime.state.mediaAudioAssetListing),
          listing(newRow.query.q || "", Number(newRow.query.offset), olderFailed ? 1 : 0));
        safe(runtime, 2);
        if (olderFirst) assert.deepEqual(firstFeedback, [], "Older action already stale before newer completes");
        else assert.deepEqual(runtime.observe(), afterNewer, "Late obsolete result cannot change newer state/feedback");
        assert.deepEqual(runtime.observe().toasts, [
          toast(COPY.en[olderFailed ? newRow.key : "audioReadFailed"], !olderFailed)
        ]);
      });
    }
  }
}

// Collection global read state is not the audio outcome. Exercise every action
// with success while collection is nonready, and failure while collection ready.
for (const [row, collectionState, failed] of [
  [ACTIONS[0], "failed", false], [ACTIONS[1], "guarded", false], [ACTIONS[2], "loading", false],
  [ACTIONS[0], "ready", true], [ACTIONS[1], "ready", true], [ACTIONS[2], "ready", true]
]) test(`independent-outcome/${row.action}/collection-${collectionState}/audio-${failed ? "failed" : "ready"}`, async () => {
  const runtime = create("zh");
  const job = runtime.start(row.action, row.fields);
  runtime.mutate("collectionReadState", collectionState);
  runtime.settle(0, {failed});
  await job.work;
  assert.equal(runtime.state.mediaWorkspaceReadState, collectionState);
  safe(runtime);
  assert.deepEqual(runtime.observe().toasts, [toast(COPY.zh[failed ? "audioReadFailed" : row.key], failed)]);
});

const CAPABILITIES = [
  ["undefined", undefined], ["null", null], ["false", false], ["zero", 0],
  ["one", 1], ["string", "true"], ["object", {}], ["array", []], ["true", true]
];
for (const row of [ACTIONS[0], ACTIONS[2]]) {
  for (const [label, value] of CAPABILITIES) {
    test(`strict-capability/${row.action}/${label}: only exact true admits private audio GET`, async () => {
      const runtime = create("en");
      runtime.mutate(row.action === "page" ? "pageCapability" : "filterCapability", value);
      const before = runtime.observe().state;
      const job = runtime.start(row.action, row.fields);
      if (value === true) {
        request(runtime, job, row);
        runtime.settle(0);
      }
      await job.work;
      if (value !== true) assert.deepEqual(runtime.observe().state, before);
      safe(runtime, value === true ? 1 : 0);
      assert.deepEqual(runtime.observe().toasts, [toast(COPY.en[value === true ? row.key
        : row.action === "page" ? "audioPageUnavailable" : "audioFilterUnavailable"], value !== true)]);
    });
  }
}
for (const locale of ["vi", "zh"]) {
  for (const row of [ACTIONS[1], ACTIONS[2]]) {
    test(`localized-guard/${locale}/${row.action}: denied read has warning role and locale`, async () => {
      const runtime = create(locale);
      runtime.mutate(row.action === "page" ? "pageCapability" : "filterCapability", false);
      const job = runtime.start(row.action, row.fields);
      await job.work;
      safe(runtime, 0);
      assert.deepEqual(runtime.observe().toasts, [
        toast(COPY[locale][row.action === "page" ? "audioPageUnavailable" : "audioFilterUnavailable"], true)
      ]);
    });
  }
}

const TRANSLATION = [
  ...ACTIONS,
  {...ACTIONS[0], key: "audioReadFailed", failed: true},
  {...ACTIONS[0], key: "audioFilterUnavailable", guard: "filterCapability"},
  {...ACTIONS[2], key: "audioPageUnavailable", guard: "pageCapability"}
];
for (const mode of ["missing", "empty", "hostile"]) {
  for (const row of TRANSLATION) {
    test(`translator/${mode}/${row.key}: exact VI fallback or hostile plain text, never HTML`, async () => {
      const runtime = create("en");
      runtime.translation(mode);
      if (row.guard) runtime.mutate(row.guard, false);
      const job = runtime.start(row.action, row.fields);
      if (!row.guard) runtime.settle(0, {failed: row.failed});
      await job.work;
      if (!row.guard && !row.failed) assert.deepEqual(plain(runtime.state.mediaAudioAssets), [asset()],
        "Frozen customer DTO remains literal, not translated");
      safe(runtime, row.guard ? 0 : 1);
      assert.deepEqual(runtime.observe().toasts, [
        toast(mode === "hostile" ? CUSTOMER : COPY.vi[row.key], row.failed || Boolean(row.guard))
      ]);
    });
  }
}

for (const outcome of ["ready", "empty", "failed", "stale-success", "stale-failed"]) {
  test(`raw-reader/${outcome}: result contract distinguishes failed from empty without new global state`, async () => {
    const runtime = create("en"), before = unrelated(runtime.state);
    const work = runtime.readAudio({q: "RAW_QUERY"}, 100);
    assert.deepEqual(runtime.network[0].query, {limit: "50", offset: "100", q: "RAW_QUERY"});
    const stale = outcome.startsWith("stale"), failed = outcome.endsWith("failed");
    if (stale) runtime.mutate("audioEpoch");
    const stateBeforeSettle = runtime.observe().state;
    runtime.settle(0, {failed, items: outcome === "empty" ? [] : [asset()]});
    const actual = plain(await work);
    assert.deepEqual(unrelated(runtime.state), before);
    if (stale) assert.deepEqual(runtime.observe().state, stateBeforeSettle);
    else assert.deepEqual(plain(runtime.state.mediaAudioAssets), outcome === "ready" ? [asset()] : []);
    safe(runtime);
    assert.deepEqual(runtime.observe().toasts, [], "Raw reader does not own action feedback");
    assert.deepEqual(actual, stale ? {stale: true} : {
      audioAssets: outcome === "ready" ? [asset()] : [],
      listing: listing("RAW_QUERY", 100, outcome === "ready" ? 1 : 0),
      ...(failed ? {failed: true} : {})
    });
  });
}

test("real projection: invalid UUID/unavailable/truthy availability filtered; valid customer DTO retained unchanged", async () => {
  const runtime = create();
  const rows = freeze([null, asset("invalid"), asset(IDS[2], {download_available: false}),
    asset(IDS[2], {download_available: "true"}), asset(IDS[2], {download_available: 1}), asset()]);
  const before = JSON.stringify(rows);
  const work = runtime.readAudio({q: CUSTOMER}, 50);
  assert.equal(runtime.network[0].query.q, CUSTOMER, "Customer query not translated");
  runtime.settle(0, {data: {
    items: rows, has_more: true, next_offset: 100, filters: {q: CUSTOMER},
    pagination: {limit: 50, offset: 50, returned: rows.length}, source: "asset_vault_owner_scoped"
  }});
  const actual = plain(await work);
  assert.deepEqual(actual, {audioAssets: [asset()], listing: listing(CUSTOMER, 50, 1)});
  assert.deepEqual(plain(runtime.state.mediaAudioAssets), [asset()]);
  assert.equal(JSON.stringify(rows), before);
  safe(runtime);
  assert.deepEqual(runtime.observe().toasts, []);
});

test("real projection: list limit50 and validated next-offset boundary remain unchanged", async () => {
  const rows = freeze(Array.from({length: 55}, (_, index) => asset(
    `${String(index + 1).padStart(8, "0")}-1111-4111-8111-111111111111`
  )));
  const runtime = create(), work = runtime.readAudio({q: "LIMIT_QUERY"}, 100);
  runtime.settle(0, {data: {items: rows, has_more: true, next_offset: 10001}});
  const actual = plain(await work);
  assert.deepEqual(actual, {audioAssets: rows.slice(0, 50), listing: listing("LIMIT_QUERY", 100, 50, false, null)});
  safe(runtime);
});
