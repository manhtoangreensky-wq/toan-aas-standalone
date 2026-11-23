import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {imageStudioRootMetadataHistoricalSource, imageStudioRootMetadataHistoricalSnapshot} from "./helpers/image-studio-root-metadata-historical.mjs";

const read = file => fs.readFileSync(new URL("../" + file, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const contract = JSON.parse(read("tests/fixtures/image-studio-root-metadata-contract.json"));
const prior = file => execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const sources = pageMetaSources();
const beforeSources = {...sources, portal: prior("static/portal/portal.js"), i18n: prior("static/portal/portal-i18n.js")};
const proposedSources = {...beforeSources};
for (const row of contract.records) {
  const key = row.file.endsWith("portal.js") ? "portal" : "i18n";
  assert.equal(proposedSources[key].split(row.old).length - 1, 1);
  proposedSources[key] = proposedSources[key].replace(row.old, () => row.new);
}
const render = await pageMetaRenderer(sources), before = await pageMetaRenderer(beforeSources), proposal = await pageMetaRenderer(proposedSources);
const copy = {
  vi: [["Thiết kế ảnh", "Lưu ý tưởng, ảnh tham khảo và các phương án thiết kế tại một nơi."], ["Bảng thiết kế ảnh", "Quản lý bảng thiết kế, so sánh phương án và chọn bước tiếp theo."]],
  en: [["Image design", "Keep ideas, reference images and design options in one place."], ["Image design boards", "Manage design boards, compare options and choose the next step."]],
  zh: [["图像设计", "在一处保存创意、参考图和设计方案。"], ["图像设计画板", "管理画板、比较方案并选择下一步。"]]
};
const id = "11111111-1111-4111-8111-111111111111";
function data(state = "ready") {
  return {capabilities: {"image-studio-view": true, "image-artboard-create": true, "image-studio-filter": true, "image-studio-page": true},
    imageStudioEnabled: true, imageStudioReadState: state,
    imageStudioReferences: {projects: [], image_assets: []},
    imageArtboards: [{id, title: "Image Creative Studio & <CUSTOMER>", state: "draft", revision: 1, creative_brief_excerpt: "CUSTOMER brief"}]};
}
const controls = html => [...html.matchAll(/<(?:input|textarea|select|button|a|option)\b[^>]*>/g)]
  .map(match => match[0].replace(/\s(?:title|placeholder|aria-label)="[^"]*"/g, ""));

test("physical root metadata source is exactly delivered BASE plus seven reviewed records", () => {
  assert.equal(contract.records.length, 7);
  for (const file of [...new Set(contract.records.map(row => row.file))]) {
    let expected = prior(file);
    for (const row of contract.records.filter(row => row.file === file)) expected = expected.replace(row.old, () => row.new);
    const hash = text => createHash("sha256").update(text).digest("hex");
    assert.equal(hash(read(file)), hash(expected), file);
  }
});

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: root title and description render in loading, failed and ready without changing controls or customer text`, () => {
    for (const [index, route] of ["/image-studio", "/image-hub"].entries()) for (const state of ["loading", "failed", "ready"]) {
      const raw = data(state), snapshot = JSON.stringify(raw), view = render(locale, route, raw), old = before(locale, route, raw);
      const html = view.qa.renderPage(view.page, {...view.context, ...raw}), oldHtml = old.qa.renderPage(old.page, {...old.context, ...raw});
      assert.equal(view.qa.localizedPageTitle(view.page, view.context), copy[locale][index][0]);
      assert.equal(view.qa.localizedPageDescription(view.page), copy[locale][index][1]);
      assert.ok(html.includes(copy[locale][index][0]) && html.includes(copy[locale][index][1]));
      assert.deepEqual(controls(html), controls(oldHtml));
      assert.equal(view.qa.supportTicketHeroSection(view.page), old.qa.supportTicketHeroSection(old.page));
      if (state === "ready") assert.match(html, /Image Creative Studio &amp; &lt;CUSTOMER&gt;/);
      assert.equal(JSON.stringify(raw), snapshot);
    }
  });
}

test("two added keys and four changed library rows are balanced and every other dictionary value is unchanged", () => {
  let addedKeys;
  for (const [index, locale] of ["vi", "en", "zh"].entries()) {
    const current = render(locale, "/image-studio", {}).messages[locale], old = before(locale, "/image-studio", {}).messages[locale];
    const added = Object.keys(current).filter(key => !Object.hasOwn(old, key)).sort();
    assert.deepEqual(added, ["imageStudioUi.page.description", "imageStudioUi.page.title"]);
    if (addedKeys) assert.deepEqual(added, addedKeys); else addedKeys = added;
    assert.equal(Object.isFrozen(current), true);
    const changes = new Map(contract.records.slice(3).map(record => {
      const row = JSON.parse(record.new.trim().replace(/,$/, ""));
      return ["imageStudioLibraryUi." + row[0], row[index + 1]];
    }));
    for (const [key, value] of Object.entries(old)) assert.equal(current[key], changes.has(key) ? changes.get(key) : value, key);
  }
});

test("eighteen other-route metadata comparisons remain unchanged", () => {
  for (const locale of ["vi", "en", "zh"]) for (const route of ["/dashboard", "/image/create", "/image-studio/" + id, "/image-hub/" + id, "/image-hub/new", "/chat"]) {
    const view = render(locale, route, {}), old = before(locale, route, {});
    assert.equal(view.qa.localizedPageTitle(view.page, view.context), old.qa.localizedPageTitle(old.page, old.context));
    assert.equal(view.qa.localizedPageDescription(view.page), old.qa.localizedPageDescription(old.page));
    assert.equal(view.qa.supportTicketHeroSection(view.page), old.qa.supportTicketHeroSection(old.page));
  }
});

test("feature-page Image workspace cards consume the current localized metadata without changing controls", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const raw = data(), view = render(locale, "/features/image", raw), old = before(locale, "/features/image", raw);
    const html = view.qa.renderPage(view.page, {...view.context, ...raw}), oldHtml = old.qa.renderPage(old.page, {...old.context, ...raw});
    assert.deepEqual(controls(html), controls(oldHtml));
    for (const [index, route] of ["/image-studio", "/image-hub"].entries()) {
      const card = html.match(new RegExp('<a class="portal-module-card" href="' + route + '"[^>]*>[\\s\\S]*?</a>'));
      assert.ok(card, route);
      assert.ok(card[0].includes("<h3>" + copy[locale][index][0] + "</h3>"), route);
      assert.ok(card[0].includes("<p>" + copy[locale][index][1] + "</p>"), route);
    }
  }
});

test("finite source projection restores only reviewed root records and does not hide other or partial changes", () => {
  for (const file of [...new Set(contract.records.map(row => row.file))]) {
    const records = contract.records.filter(row => row.file === file);
    let text = prior(file);
    for (const row of records) text = text.replace(row.old, () => row.new);
    assert.equal(imageStudioRootMetadataHistoricalSource(text, file), prior(file));
    assert.equal(imageStudioRootMetadataHistoricalSource(text + "\n/* unknown */", file), prior(file) + "\n/* unknown */");
    assert.throws(() => imageStudioRootMetadataHistoricalSource(text + records[0].new, file));
    assert.throws(() => imageStudioRootMetadataHistoricalSource(text.replace(records.at(-1).new, () => records.at(-1).old), file));
  }
});

test("finite dictionary projection preserves customer entries and rejects changed, missing or duplicated reviewed values", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const current = proposal(locale, "/image-studio", {}).messages[locale], old = before(locale, "/image-studio", {}).messages[locale];
    const entries = [...Object.entries(current), ["CUSTOMER", "Image operations hub <&>"]];
    const restored = imageStudioRootMetadataHistoricalSnapshot(entries, locale);
    assert.deepEqual(restored.slice(0, -1), Object.entries(old));
    assert.deepEqual(imageStudioRootMetadataHistoricalSnapshot(Object.entries(old), locale), Object.entries(old));
    assert.deepEqual(restored.at(-1), ["CUSTOMER", "Image operations hub <&>"]);
    const key = "imageStudioUi.page.title";
    assert.throws(() => imageStudioRootMetadataHistoricalSnapshot(entries.map(([name, value]) => [name, name === key ? "UNREVIEWED" : value]), locale));
    assert.throws(() => imageStudioRootMetadataHistoricalSnapshot(entries.filter(([name]) => name !== key), locale));
    assert.throws(() => imageStudioRootMetadataHistoricalSnapshot([...entries, entries.find(([name]) => name === key)], locale));
  }
});
