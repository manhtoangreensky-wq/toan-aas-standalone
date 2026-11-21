import assert from "node:assert/strict";
import test from "node:test";
import {execFileSync} from "node:child_process";
import {sources, runtime, collection, context, IDS, CUSTOMER, hash, ROOT} from "./helpers/media-collection-locale-runtime.mjs";

const BASE = "051b936695638a5f083396194730861dc7831da1";
const physical = sources();
const original = {...physical, raw: Object.fromEntries(Object.entries({
  portal: "static/portal/portal.js", i18n: "static/portal/portal-i18n.js"
}).map(([key, file]) => [key, execFileSync("git", ["show", `${BASE}:${file}`],
  {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true})]))};
original.hashes = Object.fromEntries(Object.entries(original.raw).map(([key, value]) => [key, hash(value)]));
const runtimes = Object.fromEntries(["vi", "en", "zh"].map(locale => [locale, runtime(physical, locale)]));
const bases = Object.fromEntries(["vi", "en", "zh"].map(locale => [locale, runtime(original, locale)]));
const expected = {
  vi: {title: "Ba gợi ý viết yêu cầu", composer: "Tạo ba gợi ý", attach: "Thêm âm thanh vào bộ sưu tập",
    placeholder: "nhạc nền, nhẹ nhàng", save: "Lưu thông tin", download: "Tải tệp",
    honest: "Sắp xếp yêu cầu đã lưu thành ba gợi ý văn bản; không tạo tệp âm thanh.",
    unsaved: "Gợi ý chưa được lưu. Hãy sao chép nếu muốn giữ lại.",
    oldNotes: ["Không gọi dịch vụ, tạo tác vụ, trừ Xu hoặc tạo đầu ra khi lưu bộ sưu tập.",
      "Không đọc, phát, kết xuất hoặc gửi âm thanh đi nơi khác.",
      "Việc gắn chỉ tạo tham chiếu riêng; tệp gốc không bị sao chép, đổi trạng thái hoặc biến thành đầu ra."]},
  en: {title: "Three text suggestions", composer: "Create three suggestions", attach: "Add audio to collection",
    placeholder: "background music, calm", save: "Save details", download: "Download file",
    honest: "Organize your saved request into three text suggestions; no audio file is created.",
    unsaved: "These suggestions are not saved. Copy them if you want to keep them.",
    oldNotes: ["Saving the collection does not call a provider, create a job, charge credits or create media output.",
      "No parsing, playback, rendering or external audio delivery occurs.",
      "Attaching creates only a private reference; the original file is not copied, reclassified or turned into output."]},
  zh: {title: "三个需求文字建议", composer: "创建三个建议", attach: "将音频添加到合集",
    placeholder: "背景音乐, 舒缓", save: "保存信息", download: "下载文件",
    honest: "将已保存的需求整理为三个文字建议，不会生成音频文件。",
    unsaved: "建议尚未保存。如需留存，请自行复制。",
    oldNotes: ["保存合集不会调用服务商、创建任务、扣费或生成媒体输出。",
      "不会解析、播放、渲染或向其他地方发送音频。",
      "添加仅创建私有参考；不会复制原文件、改变状态或生成输出。"]}
};
const escape = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
function item() {
  return {id: IDS[2], collection_id: IDS[0], asset_id: IDS[1], role: "music", title_override: CUSTOMER,
    attribution: CUSTOMER, license_note: CUSTOMER, tags: ["customer audio", "TikTok"], favorite: true,
    user_declared_duration_seconds: 90, delivery: "asset_vault_attachment_only",
    asset: {id: IDS[1], project_id: IDS[2], display_name: CUSTOMER, original_filename: CUSTOMER + ".wav",
      extension: ".wav", content_type: "audio/wav", byte_size: 44, state: "active",
      created_at: "2026-11-20T08:00:00Z", updated_at: "2026-11-20T09:00:00Z",
      archived_at: null, download_available: true}};
}
function fixture(root, {archived = false, guarded = false, composer = false} = {}) {
  const row = collection(archived ? {state: "archived"} : {});
  const route = root + "/" + row.id, audio = item();
  const result = context({row, overrides: {path: route, mediaAudioAssets: [audio.asset],
    mediaCollectionDetail: {collection: row, versions: [{revision: 6, title: CUSTOMER, prompt_mode: "background",
      created_at: row.created_at}, {revision: 7, title: CUSTOMER, prompt_mode: "background", created_at: row.updated_at}],
      items: [audio], item_count: 1, item_limit: 250},
    mediaComposer: composer ? {collection_id: row.id, revision: 7, execution: "local_deterministic_draft_only",
      provider_called: false, charge_started: false,
      directions: [1, 2, 3].map(number => ({title: "UNIQUE_DIRECTION_TITLE_" + number,
        intent: "UNIQUE_DIRECTION_INTENT_" + number, prompt: "UNIQUE_DIRECTION_PROMPT_" + number + " " + CUSTOMER}))} : {}}});
  result.capabilities["audio-asset-operation-view"] = true;
  if (guarded) for (const key of Object.keys(result.capabilities)) result.capabilities[key] = key === "media-workspace-view";
  return {route, value: result};
}
function render(r, root, options) {
  const f = fixture(root, options);
  return r.call("renderMediaWorkspaceDetail", r.page(f.route), f.value);
}
function controls(html) {
  const retained = new Set(["type", "name", "value", "href", "min", "max", "step", "maxlength", "minlength",
    "required", "disabled", "readonly", "checked", "selected", "data-portal-action", "data-portal-route",
    "data-media-collection-id", "data-media-collection-revision", "data-media-item-id",
    "data-media-audio-offset", "data-portal-form", "data-portal-no-transient", "novalidate", "rel"]);
  return [...html.matchAll(/<(form|input|select|textarea|button|a|option)\b([^>]*)>/g)].map(([, tag, attrs]) =>
    [tag, [...attrs.matchAll(/([-\w]+)(?:="([^"]*)")?/g)]
      .filter(([, key]) => retained.has(key)).map(([, key, value]) => [key, value ?? true])]);
}
for (const locale of ["vi", "en", "zh"]) for (const root of ["/media-workspace", "/audio-hub"]) {
  const r = runtimes[locale], before = bases[locale], want = expected[locale];
  test(`${locale} ${root}: real detail names the text tool and saved-audio actions in the chosen language`, () => {
    const html = render(r, root);
    for (const text of [want.title, want.composer, want.attach, want.save, want.download, want.honest, want.unsaved])
      assert.ok(html.includes(escape(text)), "Missing useful localized output: " + text);
    assert.ok(html.includes(`placeholder="${escape(want.placeholder)}"`), "App-owned tag example must follow locale");
  });
  test(`${locale} ${root}: explanatory-only nodes disappear while all actual forms and controls remain`, () => {
    const html = render(r, root), old = render(before, root);
    const oldNotes = [...old.matchAll(/<span class="portal-form-note">([\s\S]*?)<\/span>/g)].map(match => match[1]);
    for (const text of want.oldNotes) assert.ok(oldNotes.includes(escape(text)), "BASE fixture actually exercises removed note");
    assert.ok(!html.includes("portal-media-detail-boundary"), "Do not leave the explanatory boundary or an empty card");
    // This catches losing an actual control while deleting an adjacent note.
    assert.deepEqual(controls(html), controls(old), "Only copy/note nodes may change, never action contracts");
    const notes = [...html.matchAll(/<span class="portal-form-note">([\s\S]*?)<\/span>/g)].map(match => match[1]);
    for (const text of want.oldNotes) assert.ok(!notes.includes(escape(text)), "Do not retain redundant technical note");
  });
  test(`${locale} ${root}: saved English/customer content, history, audio links and real suggestion output survive`, () => {
    const html = render(r, root, {composer: true}), old = render(before, root, {composer: true});
    const result = html.match(/<div class="portal-media-composer-result">([\s\S]*?)<\/div>/)?.[1];
    assert.ok(result, "An accepted genuine suggestion receipt must actually render its result");
    assert.equal([...result.matchAll(/<article>/g)].length, 3);
    for (const number of [1, 2, 3]) for (const kind of ["TITLE", "INTENT", "PROMPT"])
      assert.ok(result.includes(`UNIQUE_DIRECTION_${kind}_${number}`), "No real suggestion may be silently lost");
    assert.ok(html.includes(escape(CUSTOMER)), "Customer content is not fixed application copy");
    assert.ok(!html.includes("<img src=x"), "Customer HTML stays text, never markup");
    for (const action of ["media-collection-update", "media-collection-compose", "media-item-attach",
      "media-item-update", "media-item-detach", "media-collection-restore-version", "media-audio-operation-handoff"])
      assert.ok(html.includes(`data-portal-action="${action}"`), "Actual action must remain: " + action);
    assert.ok(html.includes(`/api/v1/asset-vault/${IDS[1]}/download`));
    assert.deepEqual(controls(html), controls(old));
  });
  test(`${locale} ${root}: archived and permission-limited controls keep their exact original contracts`, () => {
    for (const options of [{archived: true}, {guarded: true}])
      assert.deepEqual(controls(render(r, root, options)), controls(render(before, root, options)));
  });
}
test("suggestions with an unaccepted execution or provider/charge flag never render a result", () => {
  const r = runtimes.vi;
  for (const patch of [{execution: "unknown"}, {provider_called: true}, {charge_started: true}]) {
    const f = fixture("/media-workspace", {composer: true});
    Object.assign(f.value.mediaComposer, patch);
    const html = r.call("renderMediaWorkspaceDetail", r.page(f.route), f.value);
    assert.ok(!html.includes("portal-media-composer-result"));
    assert.ok(!html.includes("UNIQUE_DIRECTION_"));
  }
});
for (const root of ["/media-workspace", "/audio-hub"]) {
  test(`${root}: a missing translator uses useful Vietnamese copy without rewriting customer values`, () => {
    const r = runtime(physical, "en"); r.missingTranslator(true);
    const html = render(r, root), want = expected.vi;
    for (const value of [want.title, want.attach, want.honest, want.unsaved]) assert.ok(html.includes(escape(value)));
    assert.ok(html.includes(`placeholder="${escape(want.placeholder)}"`));
    assert.ok(html.includes(escape(CUSTOMER))); assert.deepEqual(r.attempts(), []);
  });
}
test("full physical bundles remain observed through one exposure with no application replacement or side effects", () => {
  for (const r of Object.values(runtimes)) {
    assert.equal(r.binding.exposureCount, 1); assert.equal(r.binding.replacedProductionFunctions, 0);
    assert.equal(r.binding.hashes.portal, hash(physical.raw.portal));
    assert.equal(r.binding.hashes.i18n, hash(physical.raw.i18n));
    assert.deepEqual(r.attempts(), []);
    assert.ok(Object.isFrozen(r.messages)); assert.ok(Object.isFrozen(r.messages.vi));
    assert.deepEqual(Object.keys(r.messages.vi).sort(), Object.keys(r.messages.en).sort());
    assert.deepEqual(Object.keys(r.messages.vi).sort(), Object.keys(r.messages.zh).sort());
  }
});
