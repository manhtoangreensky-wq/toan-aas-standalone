import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const portal = fs.readFileSync(new URL("../static/portal/portal.js", import.meta.url), "utf8");
const i18n = fs.readFileSync(new URL("../static/portal/portal-i18n.js", import.meta.url), "utf8");
const anchor = "  window.TOANAASPortal = Object.freeze({";
assert.equal(portal.split(anchor).length - 1, 1);
const values = ["1:1", "4:5", "3:4", "16:9", "9:16", "3:2", "2:3", "custom"];
const labels = {
  vi: ["1:1 · Vuông", "4:5 · Dọc", "3:4 · Dọc", "16:9 · Ngang", "9:16 · Dọc", "3:2 · Ngang", "2:3 · Dọc", "Tỷ lệ tùy chỉnh"],
  en: ["1:1 · Square", "4:5 · Portrait", "3:4 · Portrait", "16:9 · Landscape", "9:16 · Portrait", "3:2 · Landscape", "2:3 · Portrait", "Custom ratio"],
  zh: ["1:1 · 方形", "4:5 · 竖版", "3:4 · 竖版", "16:9 · 横版", "9:16 · 竖版", "3:2 · 横版", "2:3 · 竖版", "自定义比例"]
};
const fallback = {vi: "Định dạng mong muốn", en: "Preferred format", zh: "期望格式"};
function runtime(locale) {
  const noop = () => {};
  const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
    getElementById: () => null, documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null,
      classList: {add: noop, remove: noop}}, body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop}};
  const window = {document, navigator: {language: locale}, location: {pathname: "/image-studio", search: ""},
    addEventListener: noop, dispatchEvent: noop, matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: {getItem: () => null, setItem: noop}, setTimeout: noop, clearTimeout: noop};
  const box = vm.createContext({window, document, navigator: window.navigator, location: window.location,
    URL, URLSearchParams, Intl, console, setTimeout: noop, clearTimeout: noop});
  vm.runInContext(i18n, box);
  vm.runInContext(portal.replace(anchor, "  window.__optionsQA = {imageStudioArtboardFields,imageStudioArtboardValues,imageStudioFormatLabel};\n" + anchor), box);
  window.TOANAASI18n.setLocale(locale, {emit: false});
  return {qa: window.__optionsQA, removeTranslator: () => { delete window.TOANAASI18n; }};
}
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: ratio and format options use readable labels while retaining their values`, () => {
    const {qa} = runtime(locale), fields = JSON.parse(JSON.stringify(qa.imageStudioArtboardFields({})));
    const ratio = fields.find(row => row.name === "aspect_ratio"), format = fields.find(row => row.name === "output_format");
    assert.deepEqual(ratio.options.map(row => row[0]), values);
    assert.deepEqual(ratio.options.map(row => row[1]), labels[locale]);
    assert.deepEqual(format.options, [["png", "PNG"], ["jpg", "JPG"], ["webp", "WebP"]]);
    assert.equal(qa.imageStudioFormatLabel("unknown"), fallback[locale]);
  });
}
test("known ratio values and existing unknown-value default remain unchanged", () => {
  const {qa} = runtime("vi");
  for (const value of values) assert.equal(qa.imageStudioArtboardValues({aspect_ratio: value}).aspect_ratio, value);
  assert.equal(qa.imageStudioArtboardValues({aspect_ratio: "unknown"}).aspect_ratio, "1:1");
  for (const [value, label] of [["PNG", "PNG"], ["jpg", "JPG"], ["WebP", "WebP"]]) assert.equal(qa.imageStudioFormatLabel(value), label);
});
test("missing translation service retains readable Vietnamese ratio and format labels", () => {
  const {qa, removeTranslator} = runtime("en");
  removeTranslator();
  const ratio = qa.imageStudioArtboardFields({}).find(row => row.name === "aspect_ratio");
  assert.deepEqual(JSON.parse(JSON.stringify(ratio.options.map(row => row[1]))), labels.vi);
  assert.equal(qa.imageStudioFormatLabel("unknown"), fallback.vi);
});
