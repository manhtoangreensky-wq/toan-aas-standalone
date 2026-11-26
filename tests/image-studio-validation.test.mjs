import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {imageStudioValidationHistoricalSource, imageStudioValidationHistoricalSnapshot} from "./helpers/image-studio-validation-historical.mjs";
import {imageComposerNativeLocaleHistoricalSource} from "./helpers/image-composer-native-locale-historical.mjs";

const root = new URL("../", import.meta.url), read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const contract = JSON.parse(read("tests/fixtures/image-studio-validation-contract.json"));
const before = Object.fromEntries(["integration", "portal-i18n"].map(name => [name,
  execFileSync("git", ["show", `${contract.base}:static/portal/${name}.js`], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n")]));
const current = {"integration": imageComposerNativeLocaleHistoricalSource(read("static/portal/integration.js"), "static/portal/integration.js"), "portal-i18n": imageComposerNativeLocaleHistoricalSource(read("static/portal/portal-i18n.js"), "static/portal/portal-i18n.js")};
const catalogue = contract.records.find(row => row.file.endsWith("portal-i18n.js")).new;
const rows = catalogue.split("  const IMAGE_STUDIO_VALIDATION_COPY_ROWS = [\n")[1].split("\n  ];")[0]
  .split("\n").map(line => JSON.parse(line.trim().replace(/,$/, "")));
const dictionary = new Map(rows.map(row => [row[0], row]));
const labels = {
  "Tag": "label.tag", "Tên artboard": "label.boardTitle", "Ý định direction": "label.intent",
  "Ngôn ngữ direction": "label.directionLanguage", "Tỷ lệ khung hình": "label.ratio", "Định dạng đích": "label.format",
  "Creative brief": "label.brief", "Style direction": "label.style", "Điều cần tránh": "label.avoid",
  "Tên biến thể direction": "label.optionTitle", "Loại biến thể": "label.operation", "Prompt / concept text": "label.prompt",
  "Chỉ dẫn chỉnh sửa": "label.edit", "Bố cục & visual notes": "label.composition", "Project liên kết": "label.project",
  "Ảnh gốc Asset Vault": "label.source", "Ảnh tham chiếu Asset Vault": "label.reference", "Từ khóa artboard": "label.boardSearch",
  "Từ khóa reference": "label.referenceSearch", "Mục tiêu ảnh": "label.goal", "Mục tiêu riêng": "label.customGoal",
  "Mô tả chủ thể": "label.subject", "Preset phong cách": "label.preset", "Phong cách": "label.customStyle", "Ngôn ngữ": "label.language"
};
const part = (text, start, end) => {
  const a = text.indexOf(start), b = text.indexOf(end, a);
  assert.ok(a >= 0 && b > a);
  return text.slice(a, b);
};
function runtime(sources, locale, missing = false) {
  const localeBox = {Intl}; localeBox.window = localeBox; vm.createContext(localeBox);
  vm.runInContext(sources["portal-i18n"], localeBox);
  const i18n = localeBox.TOANAASI18n; i18n.setLocale(locale, {emit: false});
  let translations = 0;
  const probe = {}, box = {Intl, window: {TOANAASI18n: missing ? undefined :
    {...i18n, t: (...args) => { translations++; return i18n.t(...args); }}}};
  vm.createContext(box);
  Object.assign(box, {
    PROMPT_UNSAFE_CONTROL_PATTERN: {test: () => probe.unsafe},
    PROMPT_QUOTED_SECRET_PATTERN: {test: () => probe.quoted},
    PROMPT_PRIVATE_KEY_PATTERN: {test: () => probe.privateKey},
    supportSensitiveContentKind: () => probe.sensitive,
    validImageStudioArtboardId: value => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value))
  });
  const source = sources.integration;
  let code = "";
  for (const name of ["IMAGE_STUDIO_INTENTS", "IMAGE_STUDIO_ASPECT_RATIOS", "IMAGE_STUDIO_OUTPUT_FORMATS", "IMAGE_STUDIO_ARTBOARD_FILTER_STATES"]) {
    const start = source.indexOf("  const " + name + " = "), end = source.indexOf(";\n", start);
    assert.ok(start >= 0 && end > start); code += source.slice(start, end + 1) + "\n";
  }
  code += part(source, "  function imageStudioArtboardFilterPayload(", "  function imageStudioListOffset(");
  code += part(source, source.includes("  const IMAGE_STUDIO_VALIDATION_LABELS =") ?
    "  const IMAGE_STUDIO_VALIDATION_LABELS =" : "  function imageStudioSecretSafetyError(", "  function imageStudioBoundaryIsSafe(");
  code += part(source, "  const IMAGE_PROMPT_COMPOSER_GOALS =", "  function imagePromptComposerVariantIndex(");
  code += "\nthis.checked={line:imageStudioLine,body:imageStudioBody,tags:imageStudioTags,reference:imageStudioReference,artboard:imageArtboardPayload,direction:imageDirectionPayload,secret:imageStudioSecretSafetyError,metadataSafety:imageStudioMetadataSafetyError,filter:imageStudioArtboardFilterPayload,composer:imagePromptComposerPayload,composerRatio:imagePromptComposerRatio,composerSafety:imagePromptComposerSafetyError};";
  vm.runInContext(code, box);
  return {api: box.checked, probe, i18n, count: () => translations};
}
function call(target, name, args, probe = {}) {
  Object.assign(target.probe, {unsafe: false, sensitive: null, quoted: false, privateKey: false}, probe);
  const input = structuredClone(args), snapshot = JSON.stringify(input);
  let result;
  try { result = {ok: true, value: JSON.parse(JSON.stringify(target.api[name](...input)))}; }
  catch (error) { result = {ok: false, name: error.name, message: error.message}; }
  assert.equal(JSON.stringify(input), snapshot, "validation must not mutate inputs");
  return result;
}
const id = "11111111-1111-4111-8111-111111111111";
const board = {title: "  CUSTOMER <&>  ", creative_brief: "  Ý tưởng khách\nGiữ nguyên  ", tags: ["Nhóm", " nhóm ", "TikTok"], project_id: id};
const direction = {title: "CUSTOMER option", operation: "create", prompt_text: "Mô tả của khách"};
const composer = {goal_code: "product", subject: "Sản phẩm của khách", ratio: "vuong", style_preset: "auto", style: "", language: "vi"};

test("physical validation source equals delivered BASE plus only the 30 approved presentation records", () => {
  assert.equal(contract.records.length, 30);
  assert.equal(rows.length, 51);
  assert.equal(Object.keys(labels).length, 25);
  for (const [name, source] of Object.entries(before)) {
    let expected = source;
    for (const row of contract.records.filter(row => row.file === `static/portal/${name}.js`)) {
      assert.equal(expected.split(row.old).length - 1, 1);
      expected = expected.replace(row.old, () => row.new);
    }
    assert.equal(current[name], expected);
  }
});

test("finite validation source inverse restores only reviewed changes and rejects missing or duplicated records", () => {
  for (const [name, source] of Object.entries(before)) {
    const file = `static/portal/${name}.js`, records = contract.records.filter(row => row.file === file);
    let candidate = source;
    for (const row of records) candidate = candidate.replace(row.old, () => row.new);
    assert.equal(imageStudioValidationHistoricalSource(candidate, file), source);
    assert.equal(imageStudioValidationHistoricalSource(source, file), source);
    assert.equal(imageStudioValidationHistoricalSource(candidate + "\n/* unknown */", file), source + "\n/* unknown */");
    assert.equal(imageStudioValidationHistoricalSource(candidate, "unrelated.js"), candidate);
    assert.throws(() => imageStudioValidationHistoricalSource(candidate + records[0].new, file));
    if (records.length > 1)
      assert.throws(() => imageStudioValidationHistoricalSource(candidate.replace(records.at(-1).new, () => records.at(-1).old), file));
  }
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  const old = runtime(before, locale), next = runtime(current, locale);
  const label = key => dictionary.get(key)[index + 1];
  const number = value => new Intl.NumberFormat({vi: "vi-VN", en: "en-US", zh: "zh-CN"}[locale]).format(value);
  const message = (key, params = {}) => dictionary.get(key)[index + 1]
    .replace(/\{([A-Za-z]+)\}/g, (whole, name) => Object.hasOwn(params, name) ? String(params[name]) : whole);
  const valid = [
    ["line", ["  A\n B  ", "CUSTOMER", 0, 180, true]], ["body", [" A\r\nB\rC ", "CUSTOMER", 100, true]],
    ["reference", [" " + id + " ", "CUSTOMER", false]], ["reference", ["", "CUSTOMER", true]],
    ["tags", [["Nhóm", " nhóm ", "TikTok"]]], ["artboard", [board]], ["direction", [direction]], ["composer", [composer]]
  ];
  for (const operation of ["edit", "upscale", "image_to_image", "remove_background"])
    valid.push(["direction", [{...direction, operation, asset_id: id, edit_instructions: "Chỉnh sửa riêng", composition_notes: "Bố cục riêng"}]]);
  for (const [caseIndex, [name, args]] of valid.entries()) test(`${locale}: valid ${name} ${caseIndex} keeps normalized payload and performs no translation`, () => {
    const count = next.count(), actual = call(next, name, args), previous = call(old, name, args);
    assert.equal(actual.ok, true);
    assert.deepEqual(actual, previous);
    assert.equal(next.count(), count);
  });
  const invalid = Object.entries(labels).map(([text, key]) =>
    ["line", ["x", text, 2, 10, false], "validation.length", {label: label(key), minimum: number(2), maximum: number(10)}]);
  invalid.push(
    ["line", ["x", "CUSTOMER media Studio <&>", 2, 10, false], "validation.length", {label: "CUSTOMER media Studio <&>", minimum: number(2), maximum: number(10)}],
    ["body", ["x".repeat(12001), "Creative brief", 12000, true], "validation.maximum", {label: label("label.brief"), maximum: number(12000)}],
    ["reference", ["invalid", "Project liên kết", false], "validation.reference", {label: label("label.project")}],
    ["tags", [Array.from({length: 21}, (_, n) => "tag" + n)], "validation.tags"],
    ["artboard", [{...board, image_intent: "invalid"}], "validation.intent"],
    ["artboard", [{...board, aspect_ratio: "7:11"}], "validation.ratio"],
    ["artboard", [{...board, output_format: "pdf"}], "validation.format"],
    ["direction", [{...direction, operation: "invalid"}], "validation.intent"],
    ["direction", [{...direction, operation: "edit"}], "validation.source"],
    ["direction", [{...direction, prompt_text: ""}], "validation.createText"],
    ["direction", [{...direction, operation: "edit", asset_id: id, prompt_text: ""}], "validation.editText"],
    ["direction", [{...direction, operation: "upscale", asset_id: id, prompt_text: ""}], "validation.visualText"],
    ["filter", [{q: "safe", state: "invalid"}], "validation.filterState"],
    ["composerRatio", ["7:11"], "composer.ratio"],
    ["composer", [{...composer, goal_code: "invalid"}], "composer.goal"],
    ["composer", [{...composer, style_preset: "invalid"}], "composer.preset"],
    ["composer", [{...composer, language: "fr"}], "composer.language"],
    ["composer", [{...composer, goal_code: "custom"}], "composer.customGoalRange"],
    ["composer", [{...composer, goal_code: "custom", custom_goal: "x"}], "composer.customGoalRange"],
    ["composer", [{...composer, custom_goal: "Customer goal"}], "composer.customGoalOnly"],
    ["composer", [{...composer, style_preset: "custom", style: "x"}], "composer.customStyleRange"],
    ["composer", [{...composer, style: "custom"}], "composer.customStyleOnly"]
  );
  for (const [caseIndex, [name, args, key, params]] of invalid.entries()) test(`${locale}: ${name} rejection ${caseIndex} uses ${key} without changing acceptance`, () => {
    const previous = call(old, name, args), actual = call(next, name, args);
    assert.equal(previous.ok, false); assert.equal(actual.ok, false);
    assert.equal(actual.name, previous.name);
    assert.equal(actual.message, message(key, params));
  });
  const safety = [
    ["secret", ["safe"], "unsafe.control", {unsafe: true}], ["secret", ["safe"], "unsafe.payment", {sensitive: "manual-payment"}],
    ["secret", ["safe"], "unsafe.secret", {sensitive: "credential"}], ["secret", ["safe"], "unsafe.secret", {quoted: true}],
    ["secret", ["safe"], "unsafe.secret", {privateKey: true}], ["metadataSafety", ["https://example.invalid"], "unsafe.link", {}],
    ["metadataSafety", ["provider_id=FAKE_CODE"], "unsafe.handle", {}], ["composerSafety", ["style của somebody"], "composer.originalStyle", {}],
    ["composerSafety", ["https://example.invalid"], "unsafe.link", {}]
  ];
  for (const [caseIndex, [name, args, key, probe]] of safety.entries()) test(`${locale}: ${name} warning ${caseIndex} is localized and supports the actual input flow`, () => {
    assert.ok(call(old, name, args, probe).value);
    assert.equal(call(next, name, args, probe).value, message(key));
    if (key === "unsafe.link") assert.doesNotMatch(message(key), /Kho tệp|File Library|文件库/);
  });
  test(`${locale}: exactly 51 balanced frozen keys are added and every existing dictionary value stays unchanged`, () => {
    const previous = old.i18n.messages[locale], actual = next.i18n.messages[locale];
    assert.equal(Object.isFrozen(actual), true);
    const added = Object.keys(actual).filter(key => !Object.hasOwn(previous, key)).sort();
    assert.deepEqual(added, rows.map(row => "imageStudioValidationUi." + row[0]).sort());
    for (const [key, value] of Object.entries(previous)) assert.equal(actual[key], value, key);
    for (const row of rows) assert.equal(actual["imageStudioValidationUi." + row[0]], row[index + 1]);
  });
  test(`${locale}: finite dictionary inverse keeps customer entries and detects unreviewed, missing and duplicated validation rows`, () => {
    const entries = [...Object.entries(next.i18n.messages[locale]), ["CUSTOMER", "media Studio <&>"]];
    const restored = imageStudioValidationHistoricalSnapshot(entries, locale);
    assert.deepEqual(restored, [...Object.entries(old.i18n.messages[locale]), ["CUSTOMER", "media Studio <&>"]]);
    assert.deepEqual(imageStudioValidationHistoricalSnapshot(Object.entries(old.i18n.messages[locale]), locale), Object.entries(old.i18n.messages[locale]));
    const key = "imageStudioValidationUi.unsafe.link";
    assert.throws(() => imageStudioValidationHistoricalSnapshot(entries.filter(([name]) => name !== key), locale));
    assert.throws(() => imageStudioValidationHistoricalSnapshot(entries.map(([name, value]) => [name, name === key ? "UNKNOWN" : value]), locale));
    assert.throws(() => imageStudioValidationHistoricalSnapshot([...entries, entries.find(([name]) => name === key)], locale));
  });
}
test("missing I18n still gives a readable Vietnamese warning and preserves an unknown customer label", () => {
  const next = runtime(current, "vi", true);
  assert.equal(call(next, "line", ["x", "Tên artboard", 2, 10, false]).message, "Nhập tên bảng thiết kế từ 2 đến 10 ký tự.");
  assert.equal(call(next, "line", ["x", "CUSTOMER media <&>", 2, 10, false]).message, "Nhập CUSTOMER media <&> từ 2 đến 10 ký tự.");
});
