import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {physicalSources, mediaRuntime, hash, plain, freeze, collection, IDS, CUSTOMER} from "./helpers/media-read-feedback-runtime.mjs";

// Owner-frozen literals: expectations are not derived from application helpers.
const COPY = freeze({
  vi: {filtered: "Đã lọc bộ sưu tập âm thanh.", all: "Đã hiển thị tất cả bộ sưu tập âm thanh.",
    page: "Đã tải danh sách bộ sưu tập âm thanh.", refreshed: "Đã làm mới danh sách bộ sưu tập âm thanh.",
    readFailed: "Chưa tải được danh sách bộ sưu tập âm thanh. Hãy thử lại.",
    detailRefreshed: "Đã làm mới thông tin bộ sưu tập âm thanh.",
    detailFailed: "Chưa tải được thông tin bộ sưu tập âm thanh. Hãy thử lại.",
    pageUnavailable: "Chưa thể chuyển trang bộ sưu tập âm thanh lúc này."},
  en: {filtered: "Audio collections filtered.", all: "All audio collections shown.",
    page: "Audio collection list loaded.", refreshed: "Audio collection list refreshed.",
    readFailed: "Could not load the audio collection list. Try again.",
    detailRefreshed: "Audio collection details refreshed.",
    detailFailed: "Could not load the audio collection details. Try again.",
    pageUnavailable: "Audio collection pages are not available right now."},
  zh: {filtered: "音频合集已筛选。", all: "已显示全部音频合集。",
    page: "音频合集列表已加载。", refreshed: "音频合集列表已刷新。",
    readFailed: "未能加载音频合集列表，请重试。", detailRefreshed: "音频合集详情已刷新。",
    detailFailed: "未能加载音频合集详情，请重试。", pageUnavailable: "暂时无法切换音频合集页面。"}
});
const OLD_QUERY = freeze({state: "archived", limit: "50", offset: "50", q: "OLD_QUERY", tag: "OLD_TAG", prompt_mode: "background"});
const ACTIONS = freeze([
  {action: "filter", key: "filtered", fields: {q: "  CUSTOMER   QUERY  ", tag: "tag", prompt_mode: "background", state: "all"},
    query: {state: "all", limit: "50", offset: "0", q: "CUSTOMER QUERY", tag: "tag", prompt_mode: "background"}},
  {action: "clear", key: "all", fields: {q: "IGNORED"}, query: {state: "all", limit: "50", offset: "0"}},
  {action: "page", key: "page", fields: {__mediaCollectionOffset: 100}, query: {...OLD_QUERY, offset: "100"}},
  {action: "listrefresh", key: "refreshed", fields: {}, query: OLD_QUERY},
  {action: "detailrefresh", key: "detailRefreshed", fields: {}, detail: true}
]);
const source = physicalSources();
const create = (locale = "vi", options = {}) => mediaRuntime(locale, {...options, source});
const drain = async () => { for (let count = 0; count < 16; count += 1) await Promise.resolve(); };
const toast = (text, failed = false) => ({
  text, role: failed ? "alert" : "status", className: failed ? "portal-toast portal-toast--warning" : "portal-toast"
});
function safe(runtime, count) {
  const seen = runtime.observe();
  assert.deepEqual(seen.forbidden, [], "No network/storage/navigation/product writes");
  assert.equal(seen.network.length, count);
  assert.ok(seen.network.every(row => row.method === "GET"));
  assert.ok(runtime.pending.every(row => row.settled), "All controlled GETs explicitly settled");
}
function assertPrimary(runtime, job, row) {
  const reads = job.indices.map(index => runtime.network[index]);
  assert.equal(reads.length, row.detail ? 3 : 4, "Actual reader request count");
  assert.deepEqual(reads.map(value => value.path), row.detail ? [
    `/api/v1/media-workspace/collections/${IDS[0]}`, "/api/v1/media-workspace/policy", "/api/v1/media-workspace/audio-assets"
  ] : [
    "/api/v1/media-workspace/summary", "/api/v1/media-workspace/policy",
    "/api/v1/media-workspace/collections", "/api/v1/media-workspace/events"
  ]);
  if (row.detail) assert.deepEqual(reads[2].query, {limit: "50", offset: "50", q: "OLD_AUDIO"});
  else assert.deepEqual(reads[2].query, row.query);
}
async function finish(runtime, job, options = {}) {
  const before = runtime.pending.length;
  runtime.settlePrimary(job, options);
  await drain();
  for (let index = before; index < runtime.pending.length; index += 1) {
    assert.equal(runtime.pending[index].kind, "secondary", "Only real detail secondary read may follow");
    runtime.settle(index);
  }
  await job.work;
}

test("binding: complete physical integration/i18n with one exposure, no replacement or inverse adapters", t => {
  const runtime = create();
  for (const key of ["integration", "i18n"]) {
    const physical = fs.readFileSync(runtime.binding.paths[key], "utf8");
    assert.equal(source.sources[key], physical);
    assert.equal(runtime.binding.hashes[key], hash(physical));
  }
  assert.equal(runtime.binding.instrumentedBytes, runtime.binding.physicalIntegrationBytes + runtime.binding.exposureBytes);
  assert.equal(runtime.binding.exposureCount, 1);
  assert.equal(runtime.binding.replacedProductionFunctions, 0);
  assert.notEqual(runtime.binding.executedIntegrationHash, source.hashes.integration);
  t.diagnostic(JSON.stringify(runtime.binding));
  safe(runtime, 0);
});

// Locale/root/action/outcome are one current-read axis. Stale/race/translator
// tables below are independent; they do not duplicate this entire product.
for (const root of ["/media-workspace", "/audio-hub"]) {
  for (const locale of ["vi", "en", "zh"]) {
    for (const row of ACTIONS) {
      const outcomes = row.detail ? ["ready", "failed"] : ["nonempty", "empty", "failed"];
      for (const outcome of outcomes) {
        test(`${root}/${locale}/${row.action}/${outcome}: feedback follows this current read and preserves GET shape`, async () => {
          const runtime = create(locale, {root, detail: row.detail});
          const job = runtime.start(row.action, row.fields);
          assertPrimary(runtime, job, row);
          assert.deepEqual(runtime.observe().toasts, [], "Never announce success before awaited data");
          const failed = outcome === "failed", empty = outcome === "empty";
          await finish(runtime, job, {failed, empty});
          assert.equal(runtime.state.mediaWorkspaceReadState, failed ? "failed" : "ready");
          if (row.detail) {
            assert.deepEqual(plain(runtime.state.mediaCollectionDetail), failed ? {} : {
              collection: collection(), versions: [{revision: 7, title: CUSTOMER}], items: [], item_count: 0, item_limit: 250
            });
            assert.equal(runtime.state.pageStates[root + "/" + IDS[0]], failed ? "guarded" : "read_only");
          } else {
            assert.deepEqual(plain(runtime.state.mediaCollections), failed || empty ? [] : [collection(IDS[1])]);
            assert.deepEqual(plain(runtime.state.mediaWorkspaceListing.filters), {
              q: row.query.q || "", tag: row.query.tag || "", prompt_mode: row.query.prompt_mode || "", state: row.query.state
            });
            const offset = Number(row.query.offset), returned = failed || empty ? 0 : 1;
            assert.deepEqual(plain(runtime.state.mediaWorkspaceListing.pagination), {
              limit: 50, offset, returned, has_more: returned > 0, next_offset: returned > 0 ? offset + 50 : null,
              previous_offset: offset >= 50 ? offset - 50 : null
            });
          }
          safe(runtime, row.detail ? (root === "/audio-hub" && !failed ? 4 : 3) : 4);
          assert.deepEqual(runtime.observe().toasts, [toast(COPY[locale][failed ? (row.detail ? "detailFailed" : "readFailed") : row.key], failed)]);
        });
      }
    }
  }
}

test("filter: an explicitly empty all-state filter gives all-collections feedback", async () => {
  const runtime = create("en");
  const job = runtime.start("filter", {q: "", tag: "", prompt_mode: "", state: "all"});
  assert.deepEqual(runtime.network[2].query, {state: "all", limit: "50", offset: "0"});
  await finish(runtime, job, {empty: true});
  safe(runtime, 4);
  assert.deepEqual(runtime.observe().toasts, [toast(COPY.en.all)]);
});

// Each action proves its own epoch gate; remaining identity boundaries are
// covered once for list and once for detail, for both success and failure.
const STALE = [
  ...ACTIONS.map(row => ({...row, boundary: row.detail ? "detailEpoch" : "listEpoch"})),
  ...["route", "session", "logout", "disabled"].flatMap(boundary => [
    {...ACTIONS[0], boundary}, {...ACTIONS[4], boundary}
  ])
];
for (const row of STALE) {
  for (const failed of [false, true]) {
    test(`stale/${row.action}/${row.boundary}/${failed ? "failure" : "success"}: silent, no merge`, async () => {
      const runtime = create("en", {root: "/audio-hub", detail: row.detail});
      const job = runtime.start(row.action, row.fields);
      assertPrimary(runtime, job, row);
      runtime.mutate(row.boundary);
      const before = runtime.observe().state;
      await finish(runtime, job, {failed});
      assert.deepEqual(runtime.observe().state, before, "Stale reader cannot replace current projection");
      safe(runtime, row.detail ? 3 : 4);
      assert.deepEqual(runtime.observe().toasts, [], "Stale action cannot emit success or failure");
    });
  }
}

for (const boundary of ["route", "session", "detailEpoch", "logout", "disabled"]) {
  test(`secondary-await/${boundary}: detail already ready is not sufficient to announce old success`, async () => {
    const runtime = create("zh", {root: "/audio-hub", detail: true});
    const job = runtime.start("detailrefresh");
    runtime.settlePrimary(job);
    await drain();
    assert.equal(runtime.state.mediaWorkspaceReadState, "ready");
    assert.equal(runtime.state.audioChangeRequestReadState, "loading");
    assert.equal(runtime.pending.length, 4, "Real secondary reader is pending");
    assert.deepEqual(runtime.observe().toasts, []);
    runtime.mutate(boundary);
    const before = runtime.observe().state;
    runtime.settle(3);
    await job.work;
    // The secondary reader has its own gates. Its existing implementation
    // deliberately does not use the detail epoch or workspace enabled flag;
    // do not invent a loader change while testing outer action feedback.
    assert.deepEqual(runtime.observe().state, {
      ...before, audioChangeRequestReadState: ["detailEpoch", "disabled"].includes(boundary) ? "ready" : before.audioChangeRequestReadState
    });
    safe(runtime, 4);
    assert.deepEqual(runtime.observe().toasts, [], "Re-check currentness after secondary await");
  });
}

// Two failure assignments and two settlement orders: never read newer global
// ready/failed to validate an older result. Same action and cross action share
// the real list epoch, not a new test-only action counter.
for (const pair of [["filter", "filter"], ["filter", "page"], ["page", "listrefresh"], ["detailrefresh", "detailrefresh"]]) {
  for (const olderFailed of [false, true]) {
    for (const olderFirst of [false, true]) {
      test(`overlap/${pair.join("-")}/old-${olderFailed ? "failed" : "ready"}/${olderFirst ? "old-first" : "new-first"}`, async () => {
        const isDetail = pair[0] === "detailrefresh";
        const runtime = create("en", {root: "/media-workspace", detail: isDetail});
        const oldRow = ACTIONS.find(row => row.action === pair[0]);
        const newRow = ACTIONS.find(row => row.action === pair[1]);
        const older = runtime.start(pair[0], oldRow.fields);
        const newer = runtime.start(pair[1], newRow.fields);
        assertPrimary(runtime, older, oldRow);
        assertPrimary(runtime, newer, newRow);
        let oldFirstFeedback;
        if (olderFirst) {
          await finish(runtime, older, {failed: olderFailed});
          oldFirstFeedback = runtime.observe().toasts;
          await finish(runtime, newer, {failed: !olderFailed});
        } else {
          await finish(runtime, newer, {failed: !olderFailed});
          const before = runtime.observe();
          await finish(runtime, older, {failed: olderFailed});
          assert.deepEqual(runtime.observe(), before, "Late obsolete response cannot change state or feedback");
        }
        assert.equal(runtime.state.mediaWorkspaceReadState, olderFailed ? "ready" : "failed");
        safe(runtime, isDetail ? 6 : 8);
        if (olderFirst) assert.deepEqual(oldFirstFeedback, [], "Superseded read silent even before newer settles");
        assert.deepEqual(runtime.observe().toasts, [
          toast(COPY.en[olderFailed ? newRow.key : (isDetail ? "detailFailed" : "readFailed")], !olderFailed)
        ]);
      });
    }
  }
}

test("secondary-await/newer-detail: same-ID newer ready detail cannot validate older refresh", async () => {
  const runtime = create("en", {root: "/audio-hub", detail: true});
  const older = runtime.start("detailrefresh");
  runtime.settlePrimary(older);
  await drain();
  assert.equal(runtime.pending[3].kind, "secondary");
  const newer = runtime.start("detailrefresh");
  await finish(runtime, newer);
  const before = runtime.observe();
  runtime.settle(3);
  await older.work;
  assert.deepEqual(runtime.observe(), before);
  safe(runtime, 8);
  assert.deepEqual(runtime.observe().toasts, [toast(COPY.en.detailRefreshed)]);
});

for (const row of ACTIONS) {
  test(`shared-read-state/${row.action}: a newer other-reader epoch cannot validate old feedback`, async () => {
    const runtime = create("en", {detail: row.detail});
    const job = runtime.start(row.action, row.fields);
    runtime.mutate(row.detail ? "listEpoch" : "detailEpoch");
    await finish(runtime, job);
    assert.equal(runtime.state.mediaWorkspaceReadState, "ready", "Locked reader behavior remains unchanged");
    safe(runtime, row.detail ? 3 : 4);
    assert.deepEqual(runtime.observe().toasts, [], "Other-reader overlap suppresses this old action feedback");
  });
}

test("detail invalid current collection: failed projection cannot produce detail success", async () => {
  const runtime = create("zh", {detail: true});
  const job = runtime.start("detailrefresh");
  await finish(runtime, job, {malformed: true});
  assert.equal(runtime.state.mediaWorkspaceReadState, "failed");
  assert.deepEqual(plain(runtime.state.mediaCollectionDetail), {});
  safe(runtime, 3);
  assert.deepEqual(runtime.observe().toasts, [toast(COPY.zh.detailFailed, true)]);
});

for (const locale of ["vi", "en", "zh"]) {
  for (const [label, capability] of [
    ["undefined", undefined], ["null", null], ["false", false], ["zero", 0],
    ["one", 1], ["string", "true"], ["object", {}], ["array", []], ["true", true]
  ]) {
    test(`page-capability/${locale}/${label}: only exact strict true admits the unchanged GET`, async () => {
      const runtime = create(locale);
      runtime.mutate("capability", capability);
      const job = runtime.start("page", ACTIONS[2].fields);
      if (capability === true) await finish(runtime, job);
      else await job.work;
      safe(runtime, capability === true ? 4 : 0);
      assert.deepEqual(runtime.observe().toasts, [
        toast(COPY[locale][capability === true ? "page" : "pageUnavailable"], capability !== true)
      ]);
    });
  }
}

// Eight feedback consumers exercise missing/empty fallback and hostile plain
// text independently, without multiplying the full locale/root/race matrix.
const TRANSLATION = [
  ...ACTIONS.map(row => ({...row, failed: false})),
  {...ACTIONS[0], key: "readFailed", failed: true},
  {...ACTIONS[4], key: "detailFailed", failed: true},
  {...ACTIONS[2], key: "pageUnavailable", guarded: true}
];
for (const mode of ["missing", "empty", "hostile"]) {
  for (const row of TRANSLATION) {
    test(`translator/${mode}/${row.key}: fallback VI or literal textContent, no customer translation`, async () => {
      const runtime = create("en", {detail: row.detail});
      runtime.translation(mode);
      if (row.guarded) runtime.mutate("capability", false);
      const job = runtime.start(row.action, row.fields);
      if (row.guarded) await job.work;
      else await finish(runtime, job, {failed: row.failed});
      if (!row.failed && !row.guarded) {
        const actual = row.detail ? runtime.state.mediaCollectionDetail.collection : runtime.state.mediaCollections[0];
        assert.deepEqual(plain(actual), collection(row.detail ? IDS[0] : IDS[1]), "Frozen customer text/DTO preserved");
      }
      safe(runtime, row.guarded ? 0 : row.detail ? 3 : 4);
      assert.deepEqual(runtime.observe().toasts, [
        toast(mode === "hostile" ? CUSTOMER : COPY.vi[row.key], row.failed || row.guarded)
      ]);
    });
  }
}

test("raw readers: existing list and detail return contracts unchanged, never own action feedback", async () => {
  for (const kind of ["list", "detail"]) {
    for (const outcome of ["ready", "empty", "failed", "stale"]) {
      if (kind === "detail" && outcome === "empty") continue;
      const runtime = create("en", {detail: kind === "detail"});
      const work = kind === "list" ? runtime.readList({q: "DTO_QUERY", tag: "", prompt_mode: "", state: "all"}, 100) : runtime.readDetail();
      const job = {indices: runtime.pending.map((_, index) => index), work};
      if (outcome === "stale") runtime.mutate(kind === "list" ? "listEpoch" : "detailEpoch");
      runtime.settlePrimary(job, {failed: outcome === "failed", empty: outcome === "empty"});
      const result = plain(await work);
      if (kind === "detail") assert.deepEqual(result, ["failed", "stale"].includes(outcome) ? null : {
        collection: collection(), versions: [{revision: 7, title: CUSTOMER}], items: [], audioAssets: []
      });
      else if (outcome === "stale") assert.deepEqual(result, {stale: true});
      else {
        const hasRows = outcome === "ready";
        assert.deepEqual(result, {
          collections: hasRows ? [collection(IDS[1])] : [], events: [],
          listing: {filters: {q: "DTO_QUERY", tag: "", prompt_mode: "", state: "all"},
            pagination: {limit: 50, offset: 100, returned: hasRows ? 1 : 0, has_more: hasRows,
              next_offset: hasRows ? 150 : null, previous_offset: 50}}
        });
      }
      safe(runtime, kind === "list" ? 4 : 3);
      assert.deepEqual(runtime.observe().toasts, []);
    }
  }
});
