import test from "node:test";
import assert from "node:assert/strict";
import {physicalSources, vaultRuntime, IDS, lifecycle, HOSTILE_TEXT} from "./helpers/vault-action-read-runtime.mjs";

// Fixed literal expectations are independent of application dictionaries/translation helpers.
const COPY = {
  vi: {
    searchQueryInvalid: "Từ khóa tìm kiếm tối đa 100 ký tự hợp lệ.",
    filterStateInvalid: "Bộ lọc trạng thái tệp không hợp lệ.",
    lifecycleReadAssetInvalid: "Tệp không hợp lệ để xem thông tin.",
    lifecycleOpenAssetInvalid: "Tệp không hợp lệ.",
    lifecycleOpenRouteRequired: "Chỉ có thể xem thông tin tệp từ kho tệp đang mở.",
    lifecycleSessionRequired: "Chưa thể xem thông tin tệp. Hãy tải lại trang và thử lại.",
    lifecycleCloseRouteRequired: "Chỉ có thể đóng thông tin tệp từ kho tệp đang mở.",
    privateReadSessionRequired: "Chưa thể xem kho tệp. Hãy tải lại trang và thử lại.",
    lifecycleLoaded: "Đã tải thông tin tệp."
  },
  en: {
    searchQueryInvalid: "Search terms must contain no more than 100 valid characters.",
    filterStateInvalid: "The file status filter is invalid.",
    lifecycleReadAssetInvalid: "This file is not valid for viewing details.",
    lifecycleOpenAssetInvalid: "The file is invalid.",
    lifecycleOpenRouteRequired: "You can view file details only from the file vault currently open.",
    lifecycleSessionRequired: "File details cannot be viewed right now. Reload the page and try again.",
    lifecycleCloseRouteRequired: "You can close file details only from the file vault currently open.",
    privateReadSessionRequired: "The file vault cannot be viewed right now. Reload the page and try again.",
    lifecycleLoaded: "File details loaded."
  },
  zh: {
    searchQueryInvalid: "搜索词最多可包含 100 个有效字符。",
    filterStateInvalid: "文件状态筛选条件无效。",
    lifecycleReadAssetInvalid: "文件无效，无法查看详情。",
    lifecycleOpenAssetInvalid: "文件无效。",
    lifecycleOpenRouteRequired: "只能在当前打开的文件库中查看文件详情。",
    lifecycleSessionRequired: "暂时无法查看文件详情，请刷新页面后重试。",
    lifecycleCloseRouteRequired: "只能在当前打开的文件库中关闭文件详情。",
    privateReadSessionRequired: "暂时无法查看文件库，请刷新页面后重试。",
    lifecycleLoaded: "文件详情已加载。"
  }
};
const source = physicalSources();
const create = (locale = "vi", options = {}) => vaultRuntime(locale, {...options, source});
const clone = value => JSON.parse(JSON.stringify(value));
function expectedToast(runtime, text, error = true) {
  assert.deepEqual(runtime.observe().toasts, [{
    text, role: error ? "alert" : "status",
    className: error ? "portal-toast portal-toast--warning" : "portal-toast"
  }]);
}
function noWrites(runtime, count = 0) {
  const seen = runtime.observe();
  assert.equal(seen.network.length, count);
  assert.ok(seen.network.every(row => row.method === "GET"));
  assert.deepEqual(seen.storageWrites, []);
  assert.deepEqual(seen.navigations, []);
}

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}/readcopy: invalid search length or NUL is localized before any read`, async () => {
    for (const q of ["x".repeat(101), "bad\0query"]) {
      const runtime = create(locale);
      const before = clone(runtime.state);
      await runtime.run("filter", {q, state: "active"});
      expectedToast(runtime, COPY[locale].searchQueryInvalid);
      assert.deepEqual(clone(runtime.state), before);
      noWrites(runtime);
    }
  });
  test(`${locale}/readcopy: invalid filter state is localized without a GET`, async () => {
    const runtime = create(locale);
    await runtime.run("filter", {q: "", state: "INVALID_STATE"});
    expectedToast(runtime, COPY[locale].filterStateInvalid);
    noWrites(runtime);
  });
  test(`${locale}/readcopy: direct lifecycle invalid ID retains rejected-Promise contract`, async () => {
    const runtime = create(locale);
    await assert.rejects(runtime.readLifecycle("not-a-valid-id"), error => error.message === COPY[locale].lifecycleReadAssetInvalid);
    assert.deepEqual(runtime.observe().toasts, []);
    noWrites(runtime);
  });
  test(`${locale}/readcopy: lifecycle open rejects invalid selection in the real dispatcher`, async () => {
    const runtime = create(locale);
    await runtime.run("lifecycle-open", {}, {vaultAssetId: "invalid"});
    expectedToast(runtime, COPY[locale].lifecycleOpenAssetInvalid);
    noWrites(runtime);
  });
  for (const [action, key] of [
    ["lifecycle-open", "lifecycleOpenRouteRequired"], ["lifecycle-close", "lifecycleCloseRouteRequired"]
  ]) {
    test(`${locale}/readcopy: ${action} keeps its route guard and localized feedback`, async () => {
      const runtime = create(locale, {selected: true});
      const before = clone(runtime.state);
      await runtime.run(action, {}, {route: "/dashboard", vaultAssetId: IDS[0]});
      expectedToast(runtime, COPY[locale][key]);
      assert.deepEqual(clone(runtime.state), before);
      noWrites(runtime);
    });
  }
  test(`${locale}/readcopy: lifecycle-view capability remains required`, async () => {
    const runtime = create(locale);
    runtime.state.capabilities["asset-vault-lifecycle-view"] = false;
    await runtime.run("lifecycle-open", {}, {vaultAssetId: IDS[0]});
    expectedToast(runtime, COPY[locale].lifecycleSessionRequired);
    noWrites(runtime);
  });
  for (const action of ["filter", "page"]) {
    test(`${locale}/readcopy: ${action} keeps refresh capability and localized feedback`, async () => {
      const runtime = create(locale);
      runtime.mutate("capability", false);
      await runtime.run(action, {q: "", state: "active", __assetVaultOffset: 50});
      expectedToast(runtime, COPY[locale].privateReadSessionRequired);
      noWrites(runtime);
    });
  }
  test(`${locale}/readcopy: successful lifecycle open shows localized details-loaded feedback`, async () => {
    const runtime = create(locale);
    const work = runtime.run("lifecycle-open", {}, {vaultAssetId: IDS[0]});
    assert.equal(runtime.pending.length, 1);
    assert.deepEqual(runtime.network[0], {path: `/api/v1/asset-vault/${IDS[0]}/lifecycle`, method: "GET", query: {}});
    runtime.settle(0);
    await work;
    expectedToast(runtime, COPY[locale].lifecycleLoaded, false);
    assert.deepEqual(clone(runtime.state.assetVaultLifecycle), {asset_id: IDS[0], lifecycle: lifecycle(), readState: "ready"});
    noWrites(runtime, 1);
  });
  test(`${locale}/readcopy: failed lifecycle open stays guarded and never invents success`, async () => {
    const runtime = create(locale);
    const work = runtime.run("lifecycle-open", {}, {vaultAssetId: IDS[0]});
    runtime.settle(0, {failed: true});
    await work;
    assert.deepEqual(runtime.observe().toasts, []);
    assert.deepEqual(clone(runtime.state.assetVaultLifecycle), {asset_id: IDS[0], lifecycle: null, readState: "guarded"});
    noWrites(runtime, 1);
  });
  for (const boundary of ["route", "session", "selection", "lifecycleEpoch"]) {
    test(`${locale}/readcopy: stale lifecycle open after ${boundary} cannot notify or overwrite`, async () => {
      const runtime = create(locale);
      const work = runtime.run("lifecycle-open", {}, {vaultAssetId: IDS[0]});
      runtime.mutate(boundary);
      const before = clone(runtime.state);
      runtime.settle(0);
      await work;
      assert.deepEqual(runtime.observe().toasts, []);
      assert.deepEqual(clone(runtime.state), before);
      noWrites(runtime, 1);
    });
  }
}

for (const mode of ["missing", "empty", "hostile"]) {
  test(`readcopy/translation/${mode}: fixed validation still uses fallback/plain text`, async () => {
    const runtime = create("en");
    runtime.translation(mode);
    await runtime.run("filter", {q: "x".repeat(101), state: "active"});
    expectedToast(runtime, mode === "hostile" ? HOSTILE_TEXT : COPY.vi.searchQueryInvalid);
    noWrites(runtime);
  });
  test(`readcopy/translation/${mode}: details-loaded text remains plain text`, async () => {
    const runtime = create("zh");
    runtime.translation(mode);
    const work = runtime.run("lifecycle-open", {}, {vaultAssetId: IDS[0]});
    runtime.settle(0);
    await work;
    expectedToast(runtime, mode === "hostile" ? HOSTILE_TEXT : COPY.vi.lifecycleLoaded, false);
    noWrites(runtime, 1);
  });
}
test("readcopy/projection: invalid lifecycle result stays caught, null and guarded", async () => {
  const runtime = create();
  const work = runtime.readLifecycle(IDS[0]);
  runtime.settle(0, {data: {lifecycle: {state: "active"}}});
  assert.equal(await work, null);
  assert.deepEqual(runtime.observe().toasts, []);
  assert.deepEqual(clone(runtime.state.assetVaultLifecycle), {asset_id: IDS[0], lifecycle: null, readState: "guarded"});
  noWrites(runtime, 1);
});
