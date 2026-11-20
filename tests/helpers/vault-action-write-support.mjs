import assert from "node:assert/strict";
import {File} from "node:buffer";
import {ASSET_ID, PROJECT_ID, PNG_BYTES, CSRF, publicAsset, publicLifecycle} from "./vault-action-write-runtime.mjs";

export const LOCALES = ["vi", "en", "zh"];
export const OPERATIONS = ["upload", "archive", "restore"];
export const FIXED = {
  upload: "Đã lưu tệp vào Asset Vault Web.",
  archive: "Đã lưu trữ tệp khỏi Asset Vault đang hoạt động.",
  restore: "Đã khôi phục tệp vào Asset Vault đang hoạt động."
};
// Independently copied literal rows from V2; no application translator supplies expected values.
export const COPY = {
  vi: {
    upload: "Đã lưu tệp vào kho tệp.", archive: "Đã lưu trữ tệp.", restore: "Đã khôi phục tệp.",
    uploadPending: "Tệp đang được lưu. Vui lòng chờ phản hồi từ kho tệp.",
    archivePending: "Tệp đang được lưu trữ. Vui lòng chờ phản hồi từ kho tệp.",
    restorePending: "Tệp đang được kiểm tra để khôi phục. Vui lòng chờ phản hồi từ kho tệp.",
    uploadInvalid: "Hãy chọn một tệp hợp lệ trước khi lưu vào kho tệp.",
    archiveInvalid: "Mã tệp không hợp lệ.", restoreInvalid: "Tệp không hợp lệ.",
    uploadDisplay: "Tên hiển thị tối đa 120 ký tự.", uploadProject: "Dự án đính kèm không hợp lệ.",
    uploadResponse: "Kho tệp chưa trả thông tin tệp hợp lệ.",
    archiveRoute: "Chỉ có thể lưu trữ tệp từ kho tệp đang mở.", restoreRoute: "Chỉ có thể khôi phục tệp từ kho tệp đang mở.",
    archivePermission: "Chưa thể lưu trữ tệp. Hãy tải lại trang và thử lại.",
    restorePermission: "Chưa thể khôi phục tệp. Hãy tải lại trang và thử lại.",
    archiveState: "Tệp này hiện không thể lưu trữ. Hãy tải lại thông tin tệp.",
    restoreState: "Không thể khôi phục tệp này ở trạng thái hiện tại."
  },
  en: {
    upload: "The file has been saved to the file vault.", archive: "The file has been archived.", restore: "The file has been restored.",
    uploadPending: "The file is being saved. Please wait for the file vault to respond.",
    archivePending: "The file is being archived. Please wait for the file vault to respond.",
    restorePending: "The file is being checked for restoration. Please wait for the file vault to respond.",
    uploadInvalid: "Choose a valid file before saving it to the file vault.",
    archiveInvalid: "The file ID is invalid.", restoreInvalid: "The file is invalid.",
    uploadDisplay: "The display name must be no more than 120 characters.", uploadProject: "The attached project is invalid.",
    uploadResponse: "The file vault has not returned valid file information.",
    archiveRoute: "You can archive files only from the file vault currently open.", restoreRoute: "You can restore files only from the file vault currently open.",
    archivePermission: "The file cannot be archived right now. Reload the page and try again.",
    restorePermission: "The file cannot be restored right now. Reload the page and try again.",
    archiveState: "This file cannot be archived right now. Reload the file details.",
    restoreState: "This file cannot be restored in its current state."
  },
  zh: {
    upload: "文件已保存到文件库。", archive: "文件已归档。", restore: "文件已恢复。",
    uploadPending: "文件正在保存，请等待文件库响应。", archivePending: "文件正在归档，请等待文件库响应。",
    restorePending: "正在检查文件以进行恢复，请等待文件库响应。",
    uploadInvalid: "请先选择有效文件，再保存到文件库。", archiveInvalid: "文件编号无效。", restoreInvalid: "文件无效。",
    uploadDisplay: "显示名称不能超过 120 个字符。", uploadProject: "关联的项目无效。", uploadResponse: "文件库尚未返回有效的文件信息。",
    archiveRoute: "只能在当前打开的文件库中归档文件。", restoreRoute: "只能在当前打开的文件库中恢复文件。",
    archivePermission: "暂时无法归档文件，请刷新页面后重试。", restorePermission: "暂时无法恢复文件，请刷新页面后重试。",
    archiveState: "此文件目前无法归档，请重新加载文件详情。", restoreState: "此文件当前状态不允许恢复。"
  }
};
export const drain = async () => { for (let turn = 0; turn < 12; turn += 1) await Promise.resolve(); };
export const snapshot = value => JSON.parse(JSON.stringify(value));
export const postState = operation => operation === "archive" ? "archived" : "active";
export const beforeState = operation => operation === "restore" ? "archived" : "active";
export function expectToast(runtime, text, error = false) {
  assert.deepEqual(runtime.observe().toasts, [{text, role: error ? "alert" : "status",
    className: error ? "portal-toast portal-toast--warning" : "portal-toast"}]);
}
export function expectBusy(runtime, busy) {
  assert.deepEqual(runtime.busy(), {button: {disabled: busy, aria: String(busy)}, submit: {disabled: busy, aria: String(busy)}});
}
export function expectIsolated(runtime) {
  const seen = runtime.observe();
  assert.deepEqual(seen.storageWrites, []);
  assert.deepEqual(seen.navigations, []);
  assert.ok(seen.network.every(row => row.path.startsWith("/api/v1/asset-vault")));
}

// Responses are synthetic public DTO fixtures. This never replaces an application
// function: each continuation still traverses real api(), hydrators and finally.
export async function finish(runtime, work, settings = {}) {
  let done = false, failure, answeredMutation = false;
  const outcome = {message: FIXED[runtime.operation], ...settings};
  work.then(() => { done = true; }, error => { failure = error; done = true; });
  for (let turn = 0; turn < 24 && !done; turn += 1) {
    await drain();
    for (let index = 0; index < runtime.pending.length; index += 1) {
      const row = runtime.pending[index];
      if (row.settled) continue;
      if (row.kind === "mutation") {
        const state = postState(runtime.operation);
        const data = outcome.mutationData ?? {asset: publicAsset(state),
          ...(runtime.operation === "restore" ? {lifecycle: publicLifecycle(state, (outcome.revision ?? 7) + 1)} : {})};
        const response = {data, responseOk: outcome.responseOk ?? true, payloadOk: outcome.payloadOk ?? true, status: outcome.status ?? 200};
        if (outcome.message !== undefined) response.message = outcome.message;
        runtime.settle(index, response);
        answeredMutation = true;
      } else {
        const successful = outcome.responseOk !== false && outcome.payloadOk !== false;
        const state = answeredMutation && successful ? postState(runtime.operation) : beforeState(runtime.operation);
        const revision = (outcome.revision ?? 7) + (answeredMutation && successful ? 1 : 0);
        const data = row.kind === "lifecycle"
          ? (outcome.lifecycleData ?? {lifecycle: publicLifecycle(state, revision)})
          : {items: [publicAsset(state)], has_more: false, next_offset: null,
            filters: {q: "SYNTHETIC_QUERY", state: "all"},
            pagination: {limit: 50, offset: 50, returned: 1, has_more: false, next_offset: null, previous_offset: 0}};
        runtime.settle(index, {data});
      }
    }
  }
  await drain();
  assert.equal(done, true, "Controlled action must settle without real timers/network");
  if (failure) throw failure;
  await work;
}

export async function expectTransport(runtime, {revision = 7, postIndex = 0} = {}) {
  const posts = runtime.pending.filter(row => row.kind === "mutation"), row = posts[postIndex];
  assert.ok(row, "Expected real dispatcher mutation request");
  const {entry, options} = row;
  assert.equal(entry.method, "POST");
  assert.equal(entry.headers["x-csrf-token"], CSRF);
  assert.equal(entry.headers.accept, "application/json");
  assert.match(entry.headers["x-request-id"], /^[A-Za-z0-9._:-]{12,160}$/);
  assert.deepEqual(entry.query, {});
  let key;
  if (runtime.operation === "upload") {
    assert.equal(entry.path, "/api/v1/asset-vault/upload");
    assert.equal(entry.headers["content-type"], undefined, "Browser owns multipart boundary");
    assert.ok(options.body instanceof FormData);
    assert.deepEqual([...options.body.keys()], ["file", "display_name", "project_id"]);
    const file = options.body.get("file");
    assert.ok(file instanceof File);
    assert.equal(file.name, "SYNTHETIC.png");
    assert.equal(file.type, "image/png");
    assert.equal(file.size, PNG_BYTES.length);
    assert.deepEqual(Buffer.from(await file.arrayBuffer()), PNG_BYTES);
    assert.equal(options.body.get("display_name"), "SYNTHETIC DISPLAY");
    assert.equal(options.body.get("project_id"), PROJECT_ID);
    key = entry.headers["idempotency-key"];
  } else {
    assert.equal(entry.path, `/api/v1/asset-vault/${ASSET_ID}/${runtime.operation}`);
    assert.equal(entry.headers["content-type"], "application/json");
    const body = JSON.parse(options.body);
    if (runtime.operation === "archive") {
      assert.deepEqual(body, {expected_revision: revision});
      key = entry.headers["idempotency-key"];
    } else {
      assert.equal(entry.headers["idempotency-key"], undefined);
      assert.deepEqual(Object.keys(body).sort(), ["expected_revision", "idempotency_key"]);
      assert.equal(body.expected_revision, revision);
      key = body.idempotency_key;
    }
  }
  assert.match(key, /^[A-Za-z0-9._:-]{12,160}$/);
  for (const request of runtime.pending.filter(value => value.kind !== "mutation")) {
    assert.equal(request.entry.method, "GET");
    assert.equal(request.entry.headers["x-csrf-token"], undefined);
    if (request.kind === "list") assert.deepEqual(request.entry.query, {limit: "50", offset: "50", q: "SYNTHETIC_QUERY", state: "all"});
    else {
      assert.equal(request.entry.path, `/api/v1/asset-vault/${ASSET_ID}/lifecycle`);
      assert.deepEqual(request.entry.query, {});
    }
  }
  return key;
}
