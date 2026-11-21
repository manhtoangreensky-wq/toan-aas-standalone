import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {runtime, reply, boundary, receipt, IDS, ROUTE} from "./helpers/audio-review-feedback-runtime.mjs";

const messages = [
  {id: "missing", status: 200, source: "Không tìm thấy collection thuộc Web account hiện tại.",
    expected: {vi: "Không tìm thấy bộ sưu tập trong tài khoản hiện tại.", en: "This collection was not found in your account.", zh: "在当前账户中未找到该合集。"}},
  {id: "revision", status: 200, source: "Collection đã thay đổi ở phiên khác. Hãy làm mới trước khi tiếp tục.",
    expected: {vi: "Bộ sưu tập đã thay đổi. Hãy tải lại trước khi tiếp tục.", en: "This collection has changed. Reload it before continuing.", zh: "该合集已更改，请重新加载后继续。"}},
  {id: "maintenance", status: 503, source: "Audio Library & Briefing đang tạm dừng để bảo trì. WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED chưa được bật.",
    expected: {vi: "Trung tâm âm thanh đang bảo trì. Vui lòng thử lại sau.", en: "The audio workspace is under maintenance. Please try again later.", zh: "音频工作区正在维护，请稍后重试。"}}
];

test("proposed changes bind three unique records to the deployed source", () => {
  const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/audio-review-pending-contract.json", import.meta.url), "utf8"));
  assert.equal(contract.base, "cd9c5c14263e1397531056e318a9f46394a8562d");
  assert.equal(contract.records.length, 3);
  for (const file of ["static/portal/integration.js", "static/portal/portal-i18n.js"]) {
    let source = execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 20e6}).replace(/\r\n/g, "\n");
    for (const row of contract.records.filter(record => record.file === file)) {
      assert.equal(source.split(row.old).length - 1, 1, file);
      source = source.replace(row.old, () => row.new);
    }
    assert.ok(source.length > 0);
  }
});

for (const locale of ["vi", "en", "zh"]) for (const row of messages) {
  test(`${locale}/${row.id}: review error is actionable in the selected language`, async () => {
    const app = runtime(locale);
    app.respond(() => reply(boundary(), {ok: false, status: "guarded", message: row.source, httpStatus: row.status}));
    const text = await app.dispatch(), actual = app.observe();
    assert.equal(actual.network.length, 1, "No retry of the review POST");
    assert.deepEqual(actual.forbidden, []);
    assert.equal(actual.toasts.at(-1).attributes.role, "alert");
    assert.equal(text, row.expected[locale]);
  });
}

for (const kind of ["route", "logout", "revision", "disabled"]) {
  test(`old failed review response after ${kind} stays silent`, async () => {
    const app = runtime("vi"); let finish;
    app.respond(() => new Promise(resolve => { finish = resolve; }));
    const pending = app.dispatch();
    assert.equal(app.observe().network.length, 1);
    if (kind === "route") app.path("/audio-hub/" + IDS[1]);
    if (kind === "logout") app.patch({session: {authenticated: false, csrfToken: ""}});
    if (kind === "disabled") app.patch({mediaWorkspaceEnabled: false});
    if (kind === "revision") {
      const detail = app.observe().state.mediaCollectionDetail;
      app.patch({mediaCollectionDetail: {...detail, collection: {...detail.collection, revision: 8}}});
    }
    finish(reply(boundary(), {ok: false, status: "guarded", message: "OLD_RESPONSE"}));
    await pending;
    const actual = app.observe();
    assert.equal(actual.network.length, 1);
    assert.deepEqual(actual.forbidden, []);
    assert.deepEqual(actual.state.audioHubReviewPack, {});
    assert.equal(actual.pendingRAF, 0);
    assert.deepEqual(actual.toasts, []);
  });
}

test("an older failed response stays silent while a newer review request is pending", async () => {
  const app = runtime("vi"), resolvers = [];
  app.respond(() => new Promise(resolve => resolvers.push(resolve)));
  const older = app.dispatch(), current = app.dispatch();
  assert.equal(resolvers.length, 2);
  resolvers[0](reply(boundary(), {ok: false, status: "guarded", message: "OLD_RESPONSE"}));
  await older;
  const actual = app.observe();
  assert.equal(actual.network.length, 2);
  assert.equal(actual.control.disabled, true);
  assert.deepEqual(actual.forbidden, []);
  try {
    assert.deepEqual(actual.toasts, []);
  } finally {
    resolvers[1](reply(boundary(), {ok: false, status: "guarded", message: "CURRENT_RESPONSE"}));
    await current;
  }
});

test("an older failed response cannot replace a newer successful review", async () => {
  const app = runtime("vi"), resolvers = [];
  app.respond(() => new Promise(resolve => resolvers.push(resolve)));
  const older = app.dispatch(), current = app.dispatch();
  const output = receipt();
  resolvers[1](reply(output, {message: "CURRENT_SUCCESS"}));
  await current;
  assert.equal(app.observe().toasts.at(-1).text, "CURRENT_SUCCESS");
  resolvers[0](reply(boundary(), {ok: false, status: "guarded", message: "OLD_RESPONSE"}));
  await older;
  const actual = app.observe();
  assert.deepEqual(actual.state.audioHubReviewPack, output);
  assert.equal(actual.network.length, 2);
  assert.deepEqual(actual.forbidden, []);
  assert.deepEqual(actual.toasts.map(item => item.text), ["CURRENT_SUCCESS"]);
  assert.equal(actual.control.disabled, false);
});

test("a network error arriving after navigation stays silent", async () => {
  const app = runtime("vi"); let fail;
  app.respond(() => new Promise((_resolve, reject) => { fail = reject; }));
  const pending = app.dispatch();
  app.path("/audio-hub/" + IDS[1]);
  fail(Error("OLD_NETWORK_ERROR"));
  await pending;
  const actual = app.observe();
  assert.equal(actual.network.length, 1);
  assert.deepEqual(actual.forbidden, []);
  assert.deepEqual(actual.state.audioHubReviewPack, {});
  assert.deepEqual(actual.toasts, []);
});

test("a current unknown error remains visible and releases the control", async () => {
  const app = runtime("en");
  app.respond(() => reply(boundary(), {ok: false, status: "guarded", message: "CUSTOMER_ERROR"}));
  const text = await app.dispatch(), actual = app.observe();
  assert.equal(text, "CUSTOMER_ERROR");
  assert.equal(actual.toasts.at(-1).attributes.role, "alert");
  assert.equal(actual.control.disabled, false);
  assert.deepEqual(actual.busy.map(item => item.value), ["true", "false"]);
  assert.equal(actual.network.length, 1);
  assert.deepEqual(actual.forbidden, []);
});

for (const [id, value] of [
  ["prefixed", "prefix Không tìm thấy collection thuộc Web account hiện tại."],
  ["suffixed", "Collection đã thay đổi ở phiên khác. Hãy làm mới trước khi tiếp tục. suffix"],
  ["prototype", "constructor"],
  ["markup", "<img src=x onerror='customer'> & private"]
]) {
  test(`unknown ${id} error is not translated or interpreted as markup`, async () => {
    const app = runtime("en");
    app.respond(() => reply(boundary(), {ok: false, status: "guarded", message: value}));
    const text = await app.dispatch(), actual = app.observe();
    assert.equal(text, value);
    assert.equal(actual.toasts.at(-1).attributes.role, "alert");
    assert.equal(actual.network.length, 1);
    assert.equal(actual.control.disabled, false);
    assert.deepEqual(actual.forbidden, []);
  });
}

test("a current successful review still merges and focuses the result", async () => {
  const app = runtime("vi"), output = receipt();
  app.respond(() => reply(output, {message: "CURRENT_SUCCESS"}));
  assert.equal(await app.dispatch(), "CURRENT_SUCCESS");
  assert.deepEqual(app.observe().state.audioHubReviewPack, output);
  assert.equal(app.observe().pendingRAF, 1);
  app.flushRAF();
  const actual = app.observe();
  assert.deepEqual(actual.focus, [{selector: "review-status", options: {preventScroll: true}}]);
  assert.equal(actual.network[0].path, `/api/v1/media-workspace/collections/${IDS[0]}/review-pack`);
  assert.equal(actual.control.disabled, false);
  assert.deepEqual(actual.forbidden, []);
});

test("invalid review route is rejected before making a request", async () => {
  const app = runtime("vi");
  const text = await app.dispatch({route: ROUTE + "/other"});
  const actual = app.observe();
  assert.ok(text);
  assert.equal(actual.toasts.at(-1).attributes.role, "alert");
  assert.equal(actual.network.length, 0);
  assert.deepEqual(actual.forbidden, []);
});

test("an old failure cannot unlock a newer request or hide its current error", async () => {
  const app = runtime("vi"), replies = [];
  app.respond(() => new Promise(resolve => replies.push(resolve)));
  const older = app.dispatch(), newer = app.dispatch();
  replies[0](reply(boundary(), {ok: false, status: "guarded", message: "OLD_RESPONSE"}));
  await older;
  try {
    assert.deepEqual(app.observe().toasts, []);
    assert.equal(app.observe().control.disabled, true);
  } finally {
    replies[1](reply(boundary(), {ok: false, status: "guarded", message: "CURRENT_ERROR"}));
    await newer;
  }
  const actual = app.observe();
  assert.deepEqual(actual.toasts.map(item => item.text), ["CURRENT_ERROR"]);
  assert.equal(actual.control.disabled, false);
  assert.deepEqual(actual.busy.map(item => item.value), ["true", "true", "false"]);
});
