import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageStudioDetailCopyHistoricalSource, imageStudioDetailCopyHistoricalSnapshot} from "./helpers/image-studio-detail-copy-historical.mjs";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const root = new URL("../", import.meta.url);
const contract = JSON.parse(fs.readFileSync(new URL("fixtures/image-studio-detail-customer-copy-contract.json", import.meta.url)));
const read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const prior = file => execFileSync("git", ["show", contract.base + ":" + file], {cwd: root, encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const rows = contract.records.filter(record => record.file.endsWith("portal-i18n.js")).map(record => JSON.parse(record.new.trim().replace(/,$/, "")));

test("physical sources contain exactly the reviewed copy and scoped light-theme rule", () => {
  assert.equal(rows.length, 21);
  assert.equal(contract.records.length, 22);
  for (const file of ["static/portal/portal-i18n.js", "static/portal/portal-theme.css"]) {
    let expected = prior(file);
    for (const record of contract.records.filter(row => row.file === file)) {
      assert.equal(expected.split(record.old).length - 1, 1);
      expected = expected.replace(record.old, () => record.new);
    }
    assert.equal(read(file), expected);
    assert.equal(imageStudioDetailCopyHistoricalSource(expected, file), prior(file));
    assert.equal(imageStudioDetailCopyHistoricalSource(expected + "\n/* unrelated */", file), prior(file) + "\n/* unrelated */");
  }
  const copy = contract.records[1];
  assert.throws(() => imageStudioDetailCopyHistoricalSource(read(copy.file).replace(copy.new, copy.old), copy.file));
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: customer copy is translated without changing customer content`, async () => {
    const render = await pageMetaRenderer(pageMetaSources());
    const route = "/image-studio/11111111-1111-4111-8111-111111111111";
    const raw = {capabilities: {"image-studio-view": true, "image-artboard-update": true}, imageStudioEnabled: true, imageStudioReadState: "ready",
      imageArtboardDetail: {artboard: {id: "11111111-1111-4111-8111-111111111111", state: "draft", revision: 1,
        title: "Facebook & TikTok CUSTOMER", creative_brief: "CUSTOMER <brief>"}, directions: [], versions: [], events: []}};
    const snapshot = JSON.stringify(raw), rendered = render(locale, route, raw);
    const html = rendered.qa.renderPage(rendered.page, {...rendered.context, ...raw});
    for (const row of rows) assert.equal(rendered.messages[locale]["imageStudioDetailUi." + row[0]], row[index + 1]);
    assert.match(html, /Facebook &amp; TikTok CUSTOMER/);
    assert.match(html, /CUSTOMER &lt;brief&gt;/);
    assert.equal(JSON.stringify(raw), snapshot);
    assert.match(html, /data-portal-action="image-artboard-update"/);
    assert.match(html, /data-portal-action="image-direction-create"/);
  });
}

test("historical dictionary projection restores only the twenty-one reviewed keys", () => {
  for (const [index, locale] of ["vi", "en", "zh"].entries()) {
    const copy = contract.records.filter(row => row.file.endsWith("portal-i18n.js")).map(row => ({
      old: JSON.parse(row.old.trim().replace(/,$/, "")), next: JSON.parse(row.new.trim().replace(/,$/, ""))
    }));
    const extra = [123, "Facebook CUSTOMER"];
    const entries = [...copy.map(row => ["imageStudioDetailUi." + row.next[0], row.next[index + 1]]), extra];
    const restored = imageStudioDetailCopyHistoricalSnapshot(entries, locale);
    assert.deepEqual(restored.slice(0, 21), copy.map(row => ["imageStudioDetailUi." + row.old[0], row.old[index + 1]]));
    assert.equal(restored[21], extra);
    const mixed = entries.map(row => [...row]); mixed[1][1] = "UNREVIEWED";
    assert.throws(() => imageStudioDetailCopyHistoricalSnapshot(mixed, locale));
  }
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: unavailable detail never asserts an unverified cause`, async () => {
    const render = await pageMetaRenderer(pageMetaSources());
    const title = ["Chưa thể mở bảng thiết kế", "Design board could not be opened", "暂时无法打开画板"][index];
    const body = ["Vui lòng thử lại hoặc chọn bảng thiết kế khác.", "Please try again or choose another design board.", "请重试或选择其他画板。"][index];
    for (const family of ["/image-studio", "/image-hub"]) for (const state of ["loading", "failed", "ready"]) {
      const route = family + "/11111111-1111-4111-8111-111111111111";
      const raw = {capabilities: {"image-studio-view": true}, imageStudioEnabled: true, imageStudioReadState: state, imageArtboardDetail: {}};
      const result = render(locale, route, raw), html = result.qa.renderPage(result.page, {...result.context, ...raw});
      assert.ok(html.includes(title));
      assert.ok(html.includes(body));
      assert.doesNotMatch(html, /data-portal-action="image-artboard-update"/);
    }
  });
}
