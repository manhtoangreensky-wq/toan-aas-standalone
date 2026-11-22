import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {imageStudioPresentationHistoricalSource, imageStudioPresentationHistoricalSnapshot} from "./helpers/image-studio-presentation-historical.mjs";
import {imageStudioDetailCopyHistoricalSource} from "./helpers/image-studio-detail-copy-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("fixtures/image-studio-presentation-contract.json", import.meta.url)));
const root = new URL("../", import.meta.url);
const read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const line = row => "    [" + row.map(value => JSON.stringify(value)).join(", ") + "],";
const copies = contract.copy.map(([prefix, old, next]) => ({file: "static/portal/portal-i18n.js", old: line(old), new: line(next), count: 1, prefix, row: next}));
const records = [...copies, ...contract.otherRecords];

test("physical application sources equal BASE plus exactly the 23 reviewed records", () => {
  assert.equal(contract.copy.length, 19);
  assert.equal(records.length, 23);
  for (const file of [...new Set(records.map(row => row.file))]) {
    let source = execFileSync("git", ["show", contract.base + ":" + file], {cwd: root, encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
    for (const row of records.filter(row => row.file === file)) {
      assert.equal(source.split(row.old).length - 1, row.count, row.old);
      source = source.replace(row.old, () => row.new);
    }
    assert.equal(imageStudioDetailCopyHistoricalSource(read(file), file), source, file);
  }
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: physical dictionary contains all 19 plain customer messages`, () => {
    const noop = () => {};
    const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
      documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}}, body: {setAttribute: noop}};
    const window = {document, navigator: {language: locale}, location: {pathname: "/image-studio", search: ""},
      addEventListener: noop, dispatchEvent: noop, localStorage: {getItem: () => null, setItem: noop}};
    const context = vm.createContext({window, document, navigator: window.navigator, location: window.location, URL, URLSearchParams, Intl, console});
    vm.runInContext(read("static/portal/portal-i18n.js"), context);
    window.TOANAASI18n.setLocale(locale, {emit: false});
    for (const row of copies) {
      const translated = window.TOANAASI18n.t(row.prefix + row.row[0]);
      assert.equal(translated, row.row[index + 1]);
      assert.doesNotMatch(translated, /CSRF|OTP|CVV|Asset Vault|metadata|siêu dữ liệu|会话|元数据/);
    }
  });
}

test("only the two redundant boundary calls are removed, while their helper remains unchanged", () => {
  const source = read("static/portal/portal.js");
  const base = execFileSync("git", ["show", contract.base + ":static/portal/portal.js"], {cwd: root, encoding: "utf8", maxBuffer: 30e6});
  const helper = text => text.slice(text.indexOf("  function renderImageStudioBoundary() {"), text.indexOf("  function isImageHubRoute(", text.indexOf("  function renderImageStudioBoundary() {")));
  assert.equal(helper(source), helper(base));
  assert.equal(source.split("renderImageStudioBoundary()").length - 1, 1);
  assert.equal(base.split("renderImageStudioBoundary()").length - 1, 3);
});

test("historical source inverse restores exactly BASE and keeps unrelated input visible", () => {
  for (const file of [...new Set(records.map(row => row.file))]) {
    const base = execFileSync("git", ["show", contract.base + ":" + file], {cwd: root, encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
    assert.equal(imageStudioPresentationHistoricalSource(read(file), file), base);
    assert.equal(imageStudioPresentationHistoricalSource(read(file) + "\n/* UNRELATED */", file), base + "\n/* UNRELATED */");
    assert.equal(imageStudioPresentationHistoricalSource(base, file), base);
  }
  assert.throws(() => imageStudioPresentationHistoricalSource(read("static/portal/portal-i18n.js").replace(line(contract.copy[1][2]), line(contract.copy[1][1])), "static/portal/portal-i18n.js"));
});

test("historical dictionary inverse is finite, preserves unrelated tuples and rejects mixed records", () => {
  for (const [index, locale] of ["vi", "en", "zh"].entries()) {
    const untouched = [[123, "number key"], ["customer", "TikTok & Studio CUSTOMER"]];
    const entries = [...contract.copy.map(([prefix, , next]) => [prefix + next[0], next[index + 1]]), ...untouched];
    const projected = imageStudioPresentationHistoricalSnapshot(entries, locale);
    assert.deepEqual(projected.slice(0, 19), contract.copy.map(([prefix, old]) => [prefix + old[0], old[index + 1]]));
    assert.equal(projected[19], untouched[0]);
    assert.equal(projected[20], untouched[1]);
    const mixed = entries.map(row => [...row]); mixed[1][1] = "UNREVIEWED";
    assert.throws(() => imageStudioPresentationHistoricalSnapshot(mixed, locale));
    assert.equal(imageStudioPresentationHistoricalSnapshot(untouched, locale), untouched);
  }
});
