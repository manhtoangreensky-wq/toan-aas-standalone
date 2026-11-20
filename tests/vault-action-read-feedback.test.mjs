import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {physicalSources, vaultRuntime, IDS, HOSTILE_TEXT, item, lifecycle} from "./helpers/vault-action-read-runtime.mjs";

// Literal Owner-frozen expected copy, not values computed by the application.
const COPY = {
  vi: {
    refreshed: "Đã làm mới kho tệp.", filtered: "Đã lọc danh sách tệp.",
    active: "Đã hiển thị tệp đang dùng.", page: "Đã tải danh sách tệp.",
    readFailed: "Chưa tải được danh sách tệp. Hãy thử lại.",
    lifecycleFailed: "Chưa tải được thông tin tệp. Hãy thử lại."
  },
  en: {
    refreshed: "File vault refreshed.", filtered: "Files filtered.",
    active: "Active files shown.", page: "File list loaded.",
    readFailed: "Could not load the file list. Try again.",
    lifecycleFailed: "Could not load the file details. Try again."
  },
  zh: {
    refreshed: "文件库已刷新。", filtered: "文件已筛选。",
    active: "已显示可用文件。", page: "文件列表已加载。",
    readFailed: "未能加载文件列表，请重试。", lifecycleFailed: "未能加载文件详情，请重试。"
  }
};
const ACTIONS = [
  {action: "refresh", key: "refreshed", fields: {}, query: {limit: "50", offset: "50", q: "OLD_QUERY", state: "archived"}},
  {action: "filter", key: "filtered", fields: {q: "  SYNTHETIC   QUERY  ", state: "all"},
    query: {limit: "50", offset: "0", q: "SYNTHETIC QUERY", state: "all"}},
  {action: "clear", key: "active", fields: {q: "IGNORED", state: "all"}, query: {limit: "50", offset: "0"}},
  {action: "page", key: "page", fields: {__assetVaultOffset: 100},
    query: {limit: "50", offset: "100", q: "OLD_QUERY", state: "archived"}}
];
const source = physicalSources();
const create = (locale = "vi", options = {}) => vaultRuntime(locale, {...options, source});
const snapshot = value => JSON.parse(JSON.stringify(value));
const drain = async () => { for (let count = 0; count < 6; count += 1) await Promise.resolve(); };
const toast = (runtime, text, error = false) => assert.deepEqual(runtime.observe().toasts, [{
  text, role: error ? "alert" : "status",
  className: error ? "portal-toast portal-toast--warning" : "portal-toast"
}]);
function noWrites(runtime, count) {
  const seen = runtime.observe();
  assert.equal(seen.network.length, count);
  assert.ok(seen.network.every(row => row.method === "GET"));
  assert.deepEqual(seen.storageWrites, []);
  assert.deepEqual(seen.navigations, []);
}

test("source binding: executes complete physical integration/i18n, not historical inverse transformations", () => {
  const runtime = create();
  for (const key of ["integration", "i18n"]) {
    const physical = fs.readFileSync(runtime.binding.paths[key], "utf8");
    assert.equal(runtime.source.sources[key], physical);
    assert.equal(runtime.binding.hashes[key], createHash("sha256").update(physical).digest("hex"));
  }
  assert.equal(runtime.binding.instrumentedBytes,
    runtime.binding.physicalIntegrationBytes + runtime.binding.exposureBytes);
  assert.notEqual(runtime.binding.executedIntegrationHash, runtime.binding.hashes.integration);
  noWrites(runtime, 0);
});

for (const locale of ["vi", "en", "zh"]) {
  for (const row of ACTIONS) {
    for (const empty of [false, true]) {
      test(`${locale}/${row.action}: current ${empty ? "empty" : "nonempty"} ready read gives localized success`, async () => {
        const runtime = create(locale, {selected: row.action !== "refresh"});
        const work = runtime.run(row.action, row.fields);
        assert.equal(runtime.pending.length, 1);
        assert.deepEqual(runtime.network[0], {path: "/api/v1/asset-vault", method: "GET", query: row.query});
        runtime.settle(0, {items: empty ? [] : [item(IDS[1])]});
        await work;
        toast(runtime, COPY[locale][row.key]);
        assert.equal(runtime.state.assetVaultReadState, "ready");
        assert.equal(runtime.state.pageStates["/asset-vault"], "ready");
        assert.deepEqual(snapshot(runtime.state.vaultItems), empty ? [] : [item(IDS[1])]);
        assert.deepEqual(snapshot(runtime.state.assetVaultListing.filters), {
          q: row.query.q || "", state: row.query.state || "active"
        });
        const offset = Number(row.query.offset);
        assert.deepEqual(snapshot(runtime.state.assetVaultListing.pagination), {
          limit: 50, offset, returned: empty ? 0 : 1, has_more: !empty,
          next_offset: empty ? null : offset + 50, previous_offset: offset >= 50 ? offset - 50 : null
        });
        if (row.action !== "refresh") assert.deepEqual(snapshot(runtime.state.assetVaultLifecycle),
          {asset_id: "", lifecycle: null, readState: "idle"});
        noWrites(runtime, 1);
      });
    }
    test(`${locale}/${row.action}: current failed read gives localized error, never success`, async () => {
      const runtime = create(locale);
      const work = runtime.run(row.action, row.fields);
      runtime.settle(0, {failed: true});
      await work;
      toast(runtime, COPY[locale].readFailed, true);
      assert.equal(runtime.state.assetVaultReadState, "failed");
      assert.equal(runtime.state.pageStates["/asset-vault"], "guarded");
      assert.deepEqual(snapshot(runtime.state.vaultItems), []);
      assert.deepEqual(snapshot(runtime.state.assetVaultListing.pagination), {
        limit: 50, offset: Number(row.query.offset), returned: 0, has_more: false,
        next_offset: null, previous_offset: Number(row.query.offset) >= 50 ? Number(row.query.offset) - 50 : null
      });
      noWrites(runtime, 1);
    });
    for (const boundary of ["route", "session", "listEpoch", "logout", "vaultDisabled"]) {
      for (const failed of [false, true]) {
        test(`${locale}/${row.action}: ${boundary} stale ${failed ? "failure" : "success"} is silent and cannot merge`, async () => {
          const runtime = create(locale);
          const work = runtime.run(row.action, row.fields);
          runtime.mutate(boundary);
          const before = runtime.observe().state;
          runtime.settle(0, {failed});
          await work;
          assert.deepEqual(runtime.observe().toasts, []);
          assert.deepEqual(runtime.observe().state, before);
          noWrites(runtime, 1);
        });
      }
    }
  }
  test(`${locale}/filter: empty active filter uses active-files feedback, not filtered feedback`, async () => {
    const runtime = create(locale);
    const work = runtime.run("filter", {q: "", state: "active"});
    assert.deepEqual(runtime.network[0].query, {limit: "50", offset: "0"});
    runtime.settle(0, {items: []});
    await work;
    toast(runtime, COPY[locale].active);
    noWrites(runtime, 1);
  });
  test(`${locale}/refresh: current selected lifecycle plus empty ready list can succeed only after both settle`, async () => {
    const runtime = create(locale, {selected: true});
    const work = runtime.run("refresh");
    assert.deepEqual(runtime.network.map(row => row.path), [
      "/api/v1/asset-vault", `/api/v1/asset-vault/${IDS[0]}/lifecycle`
    ]);
    runtime.settle(0, {items: []});
    await Promise.resolve();
    assert.deepEqual(runtime.observe().toasts, []);
    runtime.settle(1);
    await work;
    toast(runtime, COPY[locale].refreshed);
    assert.deepEqual(snapshot(runtime.state.assetVaultLifecycle),
      {asset_id: IDS[0], lifecycle: lifecycle(), readState: "ready"});
    assert.equal(runtime.state.assetVaultReadState, "ready");
    noWrites(runtime, 2);
  });
  for (const [listFailed, lifecycleFailed, key] of [
    [true, false, "readFailed"], [false, true, "lifecycleFailed"], [true, true, "readFailed"]
  ]) {
    test(`${locale}/refresh: selected listFailed=${listFailed}, lifecycleFailed=${lifecycleFailed} never gives combined success`, async () => {
      const runtime = create(locale, {selected: true});
      const work = runtime.run("refresh");
      runtime.settle(0, {failed: listFailed});
      runtime.settle(1, {failed: lifecycleFailed});
      await work;
      toast(runtime, COPY[locale][key], true);
      assert.equal(runtime.state.assetVaultReadState, listFailed ? "failed" : "ready");
      assert.equal(runtime.state.assetVaultLifecycle.readState, lifecycleFailed ? "guarded" : "ready");
      noWrites(runtime, 2);
    });
  }
  for (const boundary of ["clear", "selection", "lifecycleEpoch"]) {
    test(`${locale}/refresh: selected lifecycle ${boundary} suppresses combined feedback`, async () => {
      const runtime = create(locale, {selected: true});
      const work = runtime.run("refresh");
      runtime.settle(0);
      await drain();
      assert.equal(runtime.state.assetVaultReadState, "ready");
      assert.deepEqual(runtime.observe().toasts, []);
      if (boundary === "clear") await runtime.run("lifecycle-close");
      else runtime.mutate(boundary);
      const selectedBefore = snapshot(runtime.state.assetVaultLifecycle);
      runtime.settle(1);
      await work;
      assert.deepEqual(runtime.observe().toasts, []);
      assert.deepEqual(snapshot(runtime.state.assetVaultLifecycle), selectedBefore);
      noWrites(runtime, 2);
    });
  }
  test(`${locale}/refresh: newer same-selection lifecycle ready state cannot validate the older refresh`, async () => {
    const runtime = create(locale, {selected: true});
    const work = runtime.run("refresh");
    const newer = runtime.readLifecycle(IDS[0]);
    const newestLifecycle = {...lifecycle(), lifecycle_revision: 9};
    runtime.settle(2, {data: {lifecycle: newestLifecycle}});
    assert.deepEqual(snapshot(await newer), newestLifecycle);
    runtime.settle(0, {items: []});
    runtime.settle(1);
    await work;
    assert.deepEqual(runtime.observe().toasts, []);
    assert.deepEqual(snapshot(runtime.state.assetVaultLifecycle),
      {asset_id: IDS[0], lifecycle: newestLifecycle, readState: "ready"});
    noWrites(runtime, 3);
  });
  test(`${locale}/refresh: malformed current lifecycle is guarded and cannot produce combined success`, async () => {
    const runtime = create(locale, {selected: true});
    const work = runtime.run("refresh");
    runtime.settle(0, {items: []});
    runtime.settle(1, {data: {lifecycle: {state: "active"}}});
    await work;
    toast(runtime, COPY[locale].lifecycleFailed, true);
    assert.equal(runtime.state.assetVaultLifecycle.readState, "guarded");
    noWrites(runtime, 2);
  });
  for (const boundary of ["route", "session", "listEpoch", "logout", "vaultDisabled"]) {
    test(`${locale}/refresh: selected refresh with stale ${boundary} remains silent`, async () => {
      const runtime = create(locale, {selected: true});
      const work = runtime.run("refresh");
      runtime.mutate(boundary);
      runtime.settle(0);
      runtime.settle(1);
      await work;
      assert.deepEqual(runtime.observe().toasts, []);
      noWrites(runtime, 2);
    });
  }
  test(`${locale}/refresh: lifecycle settling first cannot mask a later list failure`, async () => {
    const runtime = create(locale, {selected: true});
    const work = runtime.run("refresh");
    runtime.settle(1);
    await Promise.resolve();
    assert.deepEqual(runtime.observe().toasts, []);
    runtime.settle(0, {failed: true});
    await work;
    toast(runtime, COPY[locale].readFailed, true);
    noWrites(runtime, 2);
  });
  for (const failed of [false, true]) {
    test(`${locale}/overlap: older ${failed ? "failed" : "ready"} filter cannot overwrite newer page state or feedback`, async () => {
      const runtime = create(locale);
      const older = runtime.run("filter", {q: "OLDER_QUERY", state: "all"});
      const newer = runtime.run("page", {__assetVaultOffset: 100});
      runtime.settle(1, {items: []});
      await newer;
      toast(runtime, COPY[locale].page);
      const before = runtime.observe();
      runtime.settle(0, {failed});
      await older;
      assert.deepEqual(runtime.observe(), before);
      noWrites(runtime, 2);
    });
  }
}

for (const mode of ["missing", "empty", "hostile"]) {
  for (const row of ACTIONS) {
    for (const failed of [false, true]) {
      test(`translation/${mode}/${row.action}/${failed ? "error" : "success"}: fallback/plain text stays local`, async () => {
        const runtime = create("en");
        runtime.translation(mode);
        const work = runtime.run(row.action, row.fields);
        runtime.settle(0, {failed});
        await work;
        toast(runtime, mode === "hostile" ? HOSTILE_TEXT : COPY.vi[failed ? "readFailed" : row.key], failed);
        noWrites(runtime, 1);
      });
    }
  }
  test(`translation/${mode}/selected-lifecycle-error: same fallback/plain-text boundary`, async () => {
    const runtime = create("zh", {selected: true});
    runtime.translation(mode);
    const work = runtime.run("refresh");
    runtime.settle(0);
    runtime.settle(1, {failed: true});
    await work;
    toast(runtime, mode === "hostile" ? HOSTILE_TEXT : COPY.vi.lifecycleFailed, true);
    noWrites(runtime, 2);
  });
}

test("loader DTO: ready items, empty list, failed list and stale list keep array return contract", async () => {
  for (const fixture of [
    {items: [item(IDS[1])], want: [item(IDS[1])]},
    {items: [], want: []}, {failed: true, want: []}, {stale: true, want: []}
  ]) {
    const runtime = create();
    const work = runtime.readList({q: "DTO_QUERY", state: "all"}, 100);
    if (fixture.stale) runtime.mutate("listEpoch");
    runtime.settle(0, fixture);
    assert.deepEqual(snapshot(await work), fixture.want);
    assert.deepEqual(runtime.observe().toasts, [], "Raw loader never owns action feedback");
    noWrites(runtime, 1);
  }
});

test("lifecycle DTO: current success returns projected object; guarded/stale returns null", async () => {
  for (const fixture of [{}, {failed: true}, {stale: true}]) {
    const runtime = create();
    const work = runtime.readLifecycle(IDS[0]);
    if (fixture.stale) runtime.mutate("lifecycleEpoch");
    runtime.settle(0, fixture);
    assert.deepEqual(snapshot(await work), fixture.failed || fixture.stale ? null : lifecycle());
    assert.deepEqual(runtime.observe().toasts, []);
    noWrites(runtime, 1);
  }
});

test("existing guard policy: in-flight capability alone is not a new list-currentness gate", async () => {
  const runtime = create("en");
  const work = runtime.run("refresh");
  runtime.mutate("capability", false);
  runtime.settle(0);
  await work;
  toast(runtime, COPY.en.refreshed);
  assert.equal(runtime.state.assetVaultReadState, "ready");
  noWrites(runtime, 1);
});
