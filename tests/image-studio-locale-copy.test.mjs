import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {imageStudioLocaleCopyHistoricalSource, imageStudioLocaleCopyHistoricalSnapshot} from "./helpers/image-studio-locale-copy-historical.mjs";

const read = file => fs.readFileSync(new URL("../" + file, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const contract = JSON.parse(read("tests/fixtures/image-studio-locale-copy-contract.json"));
const prior = file => execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const source = read("static/portal/portal.js");
const id = "11111111-1111-4111-8111-111111111111";
const projectId = "22222222-2222-4222-8222-222222222222";
const assetId = "33333333-3333-4333-8333-333333333333";
const copy = {
  vi: ["Chi tiết bảng thiết kế", "Xem và chỉnh sửa ý tưởng, ảnh tham khảo và các phương án.", "Thiết kế ảnh"],
  en: ["Design board details", "View and edit ideas, reference images and options.", "Image design"],
  zh: ["画板详情", "查看并编辑创意、参考图和方案。", "图像设计"]
};
const labels = {
  vi: ["Tên phương án", "Loại phương án", "Ảnh gốc", "Ảnh tham khảo (không bắt buộc)", "Mô tả ý tưởng", "Chỉ dẫn chỉnh sửa", "Bố cục và ghi chú hình ảnh", "Điều cần tránh", "Thẻ"],
  en: ["Option name", "Option type", "Source image", "Reference image (optional)", "Idea description", "Editing instructions", "Composition and visual notes", "Elements to avoid", "Tags"],
  zh: ["方案名称", "方案类型", "原图", "参考图（可选）", "创意描述", "编辑说明", "构图与视觉备注", "需要避免的元素", "标签"]
};
function fields(text, translate) {
  const start = text.indexOf("  function imageStudioDirectionFields(context) {"), end = text.indexOf("  function imageStudioDirectionValues(value) {", start);
  assert.ok(start >= 0 && end > start);
  const options = [{value: "create", label: "Create"}, {value: "edit", label: "Edit"}];
  const box = {imageStudioDetailText: translate, imageStudioIntentOptions: () => options,
    imageStudioAssetOptions: context => context.assets};
  vm.createContext(box);
  vm.runInContext(text.slice(start, end) + "\nthis.fields=imageStudioDirectionFields;", box);
  return JSON.parse(JSON.stringify(box.fields({assets: [{value: assetId, label: "Facebook & TikTok CUSTOMER"}]})));
}
function data(kind = "ready") {
  return {capabilities: {"image-studio-view": true, "image-artboard-update": true, "image-artboard-create": true, "image-direction-create": true},
    imageStudioEnabled: true, imageStudioReadState: kind, imageStudioReferences: {
      projects: [{id: projectId, title: "Facebook & TikTok CUSTOMER", state: "active"}],
      image_assets: [{id: assetId, display_name: "CUSTOMER image", state: "active", available: true, extension: "png", content_type: "image/png"}]},
    imageArtboards: [{id, state: "draft", revision: 1, title: "CUSTOMER board", creative_brief_excerpt: "CUSTOMER brief"}],
    imageArtboardDetail: kind === "ready" ? {artboard: {id, state: "draft", revision: 1, title: "Facebook & TikTok CUSTOMER",
      creative_brief: "CUSTOMER <brief> & text", project_id: projectId}, directions: [], versions: [], events: []} : {}};
}
const controls = html => [...html.matchAll(/<(?:input|textarea|select|button|a)\b[^>]*>/g)].map(match => match[0].replace(/\s(?:title|placeholder|aria-label)="[^"]*"/g, ""));
const options = html => [...html.matchAll(/<option\b[^>]*>/g)].map(match => match[0]);
const beforeSources = {...pageMetaSources(), portal: prior("static/portal/portal.js"), i18n: prior("static/portal/portal-i18n.js")};

test("physical application source is exactly BASE plus the 32 reviewed records", () => {
  assert.equal(contract.records.length, 32);
  for (const file of [...new Set(contract.records.map(row => row.file))]) {
    let expected = prior(file);
    for (const record of contract.records.filter(row => row.file === file)) {
      assert.equal(expected.split(record.old).length - 1, 1);
      expected = expected.replace(record.old, () => record.new);
    }
    assert.equal(read(file), expected);
  }
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: detail metadata, customer content and controls retain their contracts`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), before = await pageMetaRenderer(beforeSources);
    for (const family of ["/image-studio", "/image-hub"]) for (const state of ["loading", "failed", "ready"]) {
      const route = family + "/" + id, raw = data(state), snapshot = JSON.stringify(raw);
      const now = render(locale, route, raw), old = before(locale, route, raw);
      const html = now.qa.renderPage(now.page, {...now.context, ...raw}), oldHtml = old.qa.renderPage(old.page, {...old.context, ...raw});
      assert.equal(now.qa.localizedPageTitle(now.page, now.context), copy[locale][0]);
      assert.equal(now.qa.localizedPageDescription(now.page), copy[locale][1]);
      assert.equal(now.qa.supportTicketHeroSection(now.page), copy[locale][2]);
      const header = now.qa.renderHeader(now.page, now.context);
      assert.ok(header.includes(copy[locale][0]) && header.includes(copy[locale][2]));
      assert.deepEqual(controls(html), controls(oldHtml)); assert.deepEqual(options(html), options(oldHtml));
      if (state === "ready") {
        assert.match(html, /Facebook &amp; TikTok CUSTOMER/); assert.match(html, /CUSTOMER &lt;brief&gt; &amp; text/);
      }
      assert.equal(JSON.stringify(raw), snapshot);
    }
  });
  test(`${locale}: nine direction fields translate without altering values, options or limits`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), lookup = render(locale, "/image-studio/" + id, data()).messages[locale];
    const current = fields(source, (key, fallback) => lookup["imageStudioDetailUi." + key] || fallback), old = fields(beforeSources.portal, () => "");
    assert.deepEqual(current.map(field => field.label), labels[locale]);
    const semantics = rows => rows.map(({label, placeholder, help, emptyLabel, ...field}) => field);
    assert.deepEqual(semantics(current), semantics(old));
    assert.equal(current.length, 9); assert.equal(current[0].required, true); assert.equal(current[1].required, true);
    assert.ok(current[2].emptyLabel.includes(["chỉ khi tạo mới", "Create only", "仅限新建"][index]));
    assert.equal(new Set(current.map(field => field.name)).size, 9);
  });
  test(`${locale}: library dictionary is exact and does not imply a selection`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), view = render(locale, "/image-hub", data());
    const dictionary = view.messages[locale];
    const library = contract.records.filter(row => row.file.endsWith("portal-i18n.js") && row.old.trim().startsWith("[") && !row.old.includes('"page.newTitle"'));
    assert.equal(library.length, 24);
    for (const record of library) {
      const row = JSON.parse(record.new.trim().replace(/,$/, ""));
      assert.equal(dictionary["imageStudioLibraryUi." + row[0]], row[index + 1]);
    }
    assert.equal(dictionary["imageStudioLibraryUi.reference.contextProject"], ["Liên kết dự án", "Link a project", "关联项目"][index]);
    assert.equal(dictionary["imageStudioLibraryUi.reference.contextAsset"], ["Ảnh tham khảo", "Reference images", "参考图"][index]);
    const html = view.qa.renderPage(view.page, {...view.context, ...data()});
    assert.match(html, /Facebook &amp; TikTok CUSTOMER/);
    const guidance = html.match(/<p\b[^>]*>(Tìm dự án và ảnh để dùng cho bảng thiết kế\.|Find projects and images for your design board\.|查找画板所需的项目和图像。)([\s\S]*?)<\/p>/);
    assert.ok(guidance, "The library renders its localized guidance");
    assert.equal(guidance[2], "", "Guidance must not promise retention of unsaved choices absent from new search results");
    for (const route of ["/image-studio", "/image-hub"]) for (const kind of ["empty", "populated", "filtered", "unavailable", "unnamed"]) {
      const raw = data();
      if (kind === "empty") {
        raw.imageStudioReferences.projects = [];
        raw.imageStudioReferences.image_assets = [];
        raw.imageArtboards = [];
      }
      if (kind === "unavailable") {
        raw.imageStudioReferences.image_assets[0].state = "unavailable";
        raw.imageStudioReferences.image_assets[0].available = false;
      }
      if (kind === "unnamed") raw.imageStudioReferences.projects[0].title = "";
      raw.imageStudioListing = {filters: {q: kind === "filtered" ? "CUSTOMER filter" : "", state: "all"}, pagination: {offset: 0, has_more: true, next_offset: 50}};
      const snapshot = JSON.stringify(raw), current = render(locale, route, raw);
      const rendered = current.qa.renderPage(current.page, {...current.context, ...raw});
      assert.ok(rendered.includes(dictionary["imageStudioLibraryUi.library.body"]));
      if (kind === "empty") assert.ok(rendered.includes(dictionary["imageStudioLibraryUi.artboard.emptyBody"]));
      if (kind === "unavailable") {
        assert.match(rendered, /class="is-unavailable"/);
        assert.ok(rendered.includes(dictionary["imageStudioLibraryUi.reference.unavailable"]));
      }
      if (kind === "unnamed") assert.ok(rendered.includes(dictionary["imageStudioLibraryUi.reference.projectFallback"]));
      assert.equal(JSON.stringify(raw), snapshot);
    }
  });
  test(`${locale}: unrelated page metadata remains unchanged`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), before = await pageMetaRenderer(beforeSources);
    for (const route of ["/dashboard", "/image/create", "/image-studio", "/image-hub", "/chat", "/asset-vault"]) {
      const now = render(locale, route, {}), old = before(locale, route, {});
      assert.equal(now.qa.localizedPageTitle(now.page, now.context), old.qa.localizedPageTitle(old.page, old.context));
      assert.equal(now.qa.localizedPageDescription(now.page), old.qa.localizedPageDescription(old.page));
      assert.equal(now.qa.supportTicketHeroSection(now.page), old.qa.supportTicketHeroSection(old.page));
    }
  });
}

test("new dictionary entries are balanced, registered and frozen", async () => {
  const render = await pageMetaRenderer(pageMetaSources()), before = await pageMetaRenderer(beforeSources);
  let keyset;
  for (const locale of ["vi", "en", "zh"]) {
    const next = render(locale, "/image-studio/" + id, data()).messages[locale];
    const old = before(locale, "/image-studio/" + id, data()).messages[locale];
    const added = Object.keys(next).filter(key => !Object.hasOwn(old, key)).sort();
    assert.equal(added.length, 22);
    if (keyset) assert.deepEqual(added, keyset); else keyset = added;
    assert.equal(Object.isFrozen(next), true);
    for (const key of added) assert.ok(typeof next[key] === "string" && next[key].trim());
  }
});

test("historical source inverse is finite and leaves unrelated changes visible", () => {
  for (const file of [...new Set(contract.records.map(row => row.file))]) {
    const current = read(file);
    assert.equal(imageStudioLocaleCopyHistoricalSource(current, file), prior(file));
    assert.equal(imageStudioLocaleCopyHistoricalSource(current + "\n/* unrelated */", file), prior(file) + "\n/* unrelated */");
    const rows = contract.records.filter(row => row.file === file);
    assert.throws(() => imageStudioLocaleCopyHistoricalSource(current + rows[0].new, file));
    if (rows.length > 1) {
      const partial = current.replace(rows.at(-1).new, () => rows.at(-1).old);
      assert.throws(() => imageStudioLocaleCopyHistoricalSource(partial, file));
    }
  }
});

test("historical dictionary inverse changes only reviewed keys and values", async () => {
  const render = await pageMetaRenderer(pageMetaSources()), before = await pageMetaRenderer(beforeSources);
  for (const locale of ["vi", "en", "zh"]) {
    const current = render(locale, "/image-studio/" + id, data()).messages[locale];
    const old = before(locale, "/image-studio/" + id, data()).messages[locale];
    const entries = [...Object.entries(current), ["CUSTOMER", "media studio Tags <&>"]];
    const restored = imageStudioLocaleCopyHistoricalSnapshot(entries, locale);
    assert.deepEqual(restored.slice(0, -1), Object.entries(old));
    assert.deepEqual(restored.at(-1), ["CUSTOMER", "media studio Tags <&>"]);
    const changed = entries.map(entry => [...entry]);
    changed.find(entry => entry[0] === "imageStudioDetailUi.field.title")[1] = "UNREVIEWED";
    assert.throws(() => imageStudioLocaleCopyHistoricalSnapshot(changed, locale));
  }
});
