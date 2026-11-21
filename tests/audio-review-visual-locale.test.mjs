import test from "node:test";
import assert from "node:assert/strict";
import {pageMetaRenderer} from "./helpers/chat-page-meta-runtime.mjs";
import {sources, runtime, collection, context} from "./helpers/media-collection-locale-runtime.mjs";
import {receipt, ACTION, ROUTE} from "./helpers/audio-review-feedback-runtime.mjs";
import {audioReviewVisualHistoricalSource as historical, audioReviewVisualHistoricalSnapshot as historicalEntries}
  from "./helpers/audio-review-visual-snapshot.mjs";
import {audioReviewPendingHistoricalSource} from "./helpers/audio-review-pending-snapshot.mjs";
import fs from "node:fs";
import {execFileSync} from "node:child_process";

const expected = {
  vi: {hub: "Trung tâm sản xuất âm thanh", one: "tệp tham khảo", many: "tệp tham khảo"},
  en: {hub: "Audio Production Hub", one: "reference file", many: "reference files"},
  zh: {hub: "音频制作中心", one: "个参考文件", many: "个参考文件"}
};
const renderHeader = await pageMetaRenderer(), source = sources();
const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/audio-review-visual-contract.json", import.meta.url), "utf8"));
const lf = text => text.replace(/\r\n/g, "\n");
for (const [file, key] of [["static/portal/portal.js", "portal"], ["static/portal/portal-i18n.js", "i18n"]]) {
  test(`${file}: historical visual source equals its base plus reviewed changes after pending projection`, () => {
    const base = lf(execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 20e6}));
    const current = audioReviewPendingHistoricalSource(lf(source.raw[key]), file);
    let expected = base;
    for (const row of contract.records.filter(row => row.file === file)) {
      assert.equal(expected.split(row.old).length - 1, 1);
      expected = expected.replace(row.old, () => row.new);
    }
    assert.equal(current, expected);
    assert.equal(historical(current, file), base);
    assert.equal(historical(base, file), base);
    assert.equal(historical("/* customer */\n" + current, file), "/* customer */\n" + base);
    for (const row of contract.records.filter(row => row.file === file)) {
      const malformed = file.endsWith("portal-i18n.js") ? row.new.replace("reference file", "UNREVIEWED") : "";
      assert.throws(() => historical(current.replace(row.new, malformed), file), /Unreviewed audio review visual/);
      assert.throws(() => historical(current + "\n" + row.new, file), /Unreviewed audio review visual/);
    }
  });
}
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: historical catalogue removes only the verified singular entry`, () => {
    const entries = Object.entries(runtime(source, locale).messages[locale]);
    const key = "audioWorkspace.review.reference", projected = historicalEntries(entries, locale);
    assert.equal(entries.filter(([name]) => name === key).length, 1);
    assert.equal(projected.length, entries.length - 1);
    assert.deepEqual(projected, entries.filter(([name]) => name !== key));
    const unrelated = entries.find(([name]) => name !== key);
    assert.equal(projected.find(([name]) => name === unrelated[0]), unrelated);
    assert.throws(() => historicalEntries([...entries, entries.find(([name]) => name === key)], locale), /Unreviewed audio review visual/);
    assert.throws(() => historicalEntries(entries.map(row => row[0] === key ? [key, "UNKNOWN"] : row), locale), /Unreviewed audio review visual/);
    assert.equal(historicalEntries(projected, locale), projected);
  });
  test(`${locale}: audio detail breadcrumb names the hub in the selected language`, () => {
    const r = renderHeader(locale, ROUTE), html = r.qa.renderHeader(r.page, r.context);
    const crumb = html.match(/<nav class="portal-crumbs"[^>]*>([\s\S]*?)<\/nav>/)?.[1];
    assert.ok(crumb);
    assert.ok(crumb.includes(`<span>${expected[locale].hub}</span>`), crumb);
  });
  for (const count of [0, 1, 2]) {
    test(`${locale}: review count ${count} uses the appropriate reference noun`, () => {
      const app = runtime(source, locale), raw = receipt(), row = collection();
      raw.review_pack.reference_summary.total = count;
      const ctx = context({row, overrides: {path: ROUTE, audioHubReviewPack: raw}});
      ctx.capabilities[ACTION] = true;
      const html = app.call("renderMediaWorkspaceDetail", app.page(ROUTE), ctx);
      assert.ok(html.includes(`<span>${count} ${count === 1 ? expected[locale].one : expected[locale].many}</span>`));
    });
  }
}
