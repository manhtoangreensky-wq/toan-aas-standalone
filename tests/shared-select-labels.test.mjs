import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {BASE, sources, runtime, freeze, clone, IDS, CUSTOMER, asset, context} from "./helpers/shared-select-labels-runtime.mjs";
import {mediaCollectionHistoricalSnapshot} from "./helpers/media-collection-locale-snapshot.mjs";

const physical = sources(), baseline = sources({baseline: true});
const LOCALES = ["vi", "en", "zh"];
const TARGETS = ["projects", "memoryNotes", "voiceProfiles"];
const FILES = ["pdfVaultAssets", "imageVaultAssets"];
const FAMILIES = [...TARGETS, ...FILES];
const KEYS = ["sharedSelect.projectFallback", "sharedSelect.noteFallback", "sharedSelect.voiceFallback", "sharedSelect.voiceDefaultSuffix"];
const COPY = {
  vi: {projects: "Dự án chưa đặt tên", memoryNotes: "Ghi chú chưa đặt tên", voiceProfiles: "Giọng chưa đặt tên", suffix: " · Mặc định"},
  en: {projects: "Untitled project", memoryNotes: "Untitled note", voiceProfiles: "Unnamed voice", suffix: " · Default"},
  zh: {projects: "未命名项目", memoryNotes: "未命名笔记", voiceProfiles: "未命名声音", suffix: " · 默认"}
};
const escape = value => String(value).replace(/[&<>'"]/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"}[char]));
const decode = value => value.replace(/&(amp|lt|gt|quot|#39);/g, (_, key) => ({amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'"}[key]));
const options = html => [...html.matchAll(/<option value="([^"]*)"([^>]*)>([\s\S]*?)<\/option>/g)]
  .map(match => ({value: decode(match[1]), selected: /\bselected\b/.test(match[2]), label: decode(match[3]), encoded: match[3]}));
const field = (family, extra = {}) => ({
  name: "source_id", label: "SYNTHETIC LABEL", control: "select", optionsFrom: family, emptyLabel: "SYNTHETIC EMPTY",
  help: "SYNTHETIC HELP & details", required: true, controlData: {"qa-ok": 'literal"&', "INVALID KEY": "drop"},
  wrapperData: {"qa-wrap": "value"}, ...extra
});
function row(family, name, id = IDS[0], extra = {}) {
  if (FILES.includes(family)) return asset(family === "pdfVaultAssets" ? "pdf" : "image", id, {display_name: name, ...extra});
  return family === "voiceProfiles" ? {id, display_name: name, tts_ready: true, is_default: false, ...extra}
    : {id, title: name, state: "active", ...extra};
}
function rendered(instance, family, rows, {enabled = true, disabled = false, selected = IDS[0], namespace = "shared-qa / scope", extraContext = {}} = {}) {
  const fields = freeze([field(family, {disabled})]), value = freeze({source_id: selected});
  const raw = freeze({...context(family, rows), ...extraContext});
  const html = instance.render(fields, enabled, raw, value, namespace);
  assert.ok(html.includes('id="portal-field-shared-qa---scope-source_id"'));
  assert.ok(html.includes('name="source_id" required aria-required="true" aria-describedby="portal-field-shared-qa---scope-source_id-help"'));
  assert.ok(html.includes('for="portal-field-shared-qa---scope-source_id"'));
  assert.ok(html.includes('id="portal-field-shared-qa---scope-source_id-help"'));
  assert.ok(html.includes('data-qa-ok="literal&quot;&amp;"') && html.includes('data-qa-wrap="value"'));
  assert.ok(!html.includes("INVALID KEY"));
  assert.equal(/<select\b[^>]* disabled>/.test(html), !enabled || disabled);
  assert.equal(options(html)[0].value, ""); assert.equal(options(html)[0].label, "SYNTHETIC EMPTY");
  assert.deepEqual(instance.attempts(), []);
  return {html, options: options(html)};
}
const keyFor = family => KEYS[TARGETS.indexOf(family)];
const nameKey = family => family === "voiceProfiles" ? "display_name" : "title";
const allInstances = locale => [runtime(physical, locale), runtime(baseline, locale)];

test("full physical source binding and one renderer-only exposure keep real i18n and zero side effects", () => {
  const instance = runtime(physical, "en");
  for (const key of ["portal", "i18n"]) {
    const raw = fs.readFileSync(physical.paths[key], "utf8");
    assert.equal(raw, physical.raw[key]);
    assert.equal(createHash("sha256").update(raw).digest("hex"), instance.binding.hashes[key]);
  }
  assert.equal(instance.binding.executedPortalBytes, instance.binding.physicalPortalBytes + instance.binding.exposureBytes);
  assert.notEqual(instance.binding.executedPortalHash, instance.binding.hashes.portal);
  assert.equal(instance.binding.exposureCount, 1);
  assert.equal(instance.currentLocale(), "en");
  assert.equal(BASE, "46423a6df9af67ac7ccabd88686d4cb42523a078");
  assert.deepEqual(instance.attempts(), []);
});

for (const locale of LOCALES) {
  test(`${locale}/catalogue: exactly four added frozen keys, equal locale keysets, all other BASE entries unchanged`, () => {
    const [now, old] = allInstances(locale);
    assert.ok(Object.isFrozen(now.messages));
    const allKeys = Object.keys(now.messages.vi).sort();
    for (const other of LOCALES) {
      assert.ok(Object.isFrozen(now.messages[other]));
      assert.deepEqual(Object.keys(now.messages[other]).sort(), allKeys);
    }
    // This four-key BASE comparison is historical; current media acceptance
    // independently checks all38 reviewed rows and the complete physical files.
    const current = Object.fromEntries(mediaCollectionHistoricalSnapshot(Object.entries(clone(now.messages[locale])), locale)),
      previous = clone(old.messages[locale]);
    assert.deepEqual(Object.keys(current).filter(key => !Object.hasOwn(previous, key)).sort(), [...KEYS].sort());
    assert.deepEqual(Object.keys(previous).filter(key => !Object.hasOwn(current, key)), []);
    for (const family of TARGETS) assert.equal(current[keyFor(family)], COPY[locale][family]);
    assert.equal(current[KEYS[3]], COPY[locale].suffix);
    for (const key of KEYS) delete current[key];
    assert.deepEqual(current, previous, "Every unrelated catalogue value remains BASE-exact");
    assert.deepEqual(Object.keys(now.messages[locale]).filter(key => key.startsWith("sharedSelect.")).sort(), [...KEYS].sort());
  });
  for (const family of TARGETS) {
    test(`${locale}/${family}: every existing falsy name gets the exact localized fallback`, () => {
      const instance = runtime(physical, locale);
      for (const value of [undefined, null, "", false, 0, NaN]) {
        const result = rendered(instance, family, [row(family, value)]);
        assert.deepEqual(result.options.slice(1).map(option => ({value: option.value, label: option.label, selected: option.selected})),
          [{value: IDS[0], label: COPY[locale][family], selected: true}]);
      }
    });
  }
  test(`${locale}/voice: default suffix applies only to strict true and is localized independently of name`, () => {
    const instance = runtime(physical, locale);
    const flags = [true, false, "true", 1, null, undefined];
    const rows = flags.map((flag, index) => row("voiceProfiles", index === 0 ? "" : "CUSTOMER VOICE", IDS[index], {is_default: flag}));
    const result = rendered(instance, "voiceProfiles", rows);
    assert.deepEqual(result.options.slice(1).map(option => option.label),
      [COPY[locale].voiceProfiles + COPY[locale].suffix, ...flags.slice(1).map(() => "CUSTOMER VOICE")]);
    const namedDefault = rendered(instance, "voiceProfiles", [row("voiceProfiles", CUSTOMER, IDS[0], {is_default: true})]);
    assert.equal(namedDefault.options[1].label, CUSTOMER + COPY[locale].suffix);
  });
  for (const family of FAMILIES) {
    test(`${locale}/${family}: customer/brand/hostile text stays literal escaped once with raw UUID selection and no input mutation`, () => {
      const instance = runtime(physical, locale), rows = [row(family, CUSTOMER)];
      const before = JSON.stringify(rows), result = rendered(instance, family, rows);
      const suffix = family === "pdfVaultAssets" ? " · 1.5 KB" : family === "imageVaultAssets" ? " · PNG · 1.5 KB" : "";
      assert.equal(result.options[1].label, CUSTOMER + suffix);
      assert.equal(result.options[1].encoded, escape(CUSTOMER + suffix));
      assert.equal(result.options[1].value, IDS[0]); assert.equal(result.options[1].selected, true);
      assert.ok(!result.html.includes("<img src=x") && !result.html.includes("&amp;lt;img"));
      assert.equal(JSON.stringify(rows), before);
      for (const settings of [{enabled: false}, {disabled: true}, {selected: ""}]) {
        const checked = rendered(instance, family, [row(family, CUSTOMER)], settings);
        assert.equal(checked.options[0].selected, settings.selected === "");
        assert.equal(checked.options[1].selected, settings.selected !== "");
      }
    });
  }
  for (const family of ["projects", "memoryNotes"]) {
    test(`${locale}/${family}: invalid and archived rows remain excluded while missing state retains original active default`, () => {
      const [now, old] = allInstances(locale);
      const rows = [null, row(family, "INVALID", "invalid"), row(family, "ARCHIVED", IDS[1], {state: "archived"}),
        row(family, "ACTIVE", IDS[0]), row(family, "DEFAULT ACTIVE", IDS[2], {state: undefined}),
        row(family, "DELETED", IDS[3], {state: "deleted"})];
      const result = rendered(now, family, rows);
      assert.deepEqual(result.options.slice(1).map(option => [option.value, option.label]), [[IDS[0], "ACTIVE"], [IDS[2], "DEFAULT ACTIVE"]]);
      assert.equal(result.html, rendered(old, family, clone(rows)).html);
    });
  }
  test(`${locale}/voice: nonready/empty rows stay excluded and raw truthy values are not normalized`, () => {
    const [now, old] = allInstances(locale);
    const rawId = `VOICE-"<&`, rows = [null, row("voiceProfiles", "NOT READY", IDS[1], {tts_ready: false}),
      row("voiceProfiles", "STRING READY", IDS[2], {tts_ready: "true"}), row("voiceProfiles", "EMPTY ID", ""),
      row("voiceProfiles", "  Facebook TikTok media studio  ", rawId)];
    const result = rendered(now, "voiceProfiles", rows, {selected: rawId});
    assert.deepEqual(result.options.slice(1).map(option => [option.value, option.label, option.selected]),
      [[rawId, "  Facebook TikTok media studio  ", true]]);
    assert.ok(result.html.includes('value="VOICE-&quot;&lt;&amp;" selected'));
    assert.equal(result.html, rendered(old, "voiceProfiles", clone(rows), {selected: rawId}).html);
  });
  for (const family of FILES) {
    test(`${locale}/${family}: real normalization/filename precedence/invalid-name exclusions remain BASE-exact`, () => {
      const [now, old] = allInstances(locale), kind = family === "pdfVaultAssets" ? "pdf" : "image";
      const rows = [asset(kind, IDS[0], {display_name: "DISPLAY FIRST", original_filename: "ORIGINAL SECOND"}),
        asset(kind, IDS[1], {display_name: "", original_filename: "  ORIGINAL \t FILE  "}),
        asset(kind, IDS[2], {display_name: "", original_filename: ""}),
        asset(kind, IDS[3], {display_name: "   ", original_filename: "TRUTHY_WHITESPACE_DOES_NOT_FALL_THROUGH"}),
        asset(kind, IDS[4], {state: "archived"}), asset(kind, "invalid")];
      const suffix = kind === "pdf" ? " · 1.5 KB" : " · PNG · 1.5 KB";
      const result = rendered(now, family, rows);
      assert.deepEqual(result.options.slice(1).map(option => [option.value, option.label]),
        [[IDS[0], "DISPLAY FIRST" + suffix], [IDS[1], "ORIGINAL FILE" + suffix]]);
      assert.equal(result.html, rendered(old, family, clone(rows)).html);
      for (const readState of ["loading", "ready", "failed", "guarded"]) {
        const extraContext = family === "pdfVaultAssets" ? {documentAssetReferenceReadState: readState}
          : {imageOperationAssetReferenceReadState: readState};
        assert.equal(rendered(now, family, clone(rows), {extraContext}).html,
          rendered(old, family, clone(rows), {extraContext}).html, "Preserve existing renderer/readState contract");
      }
      const wrongType = asset(kind, IDS[0], {content_type: kind === "pdf" ? "image/png" : "application/pdf"});
      assert.equal(rendered(now, family, [wrongType]).options.length, 1);
      assert.equal(rendered(old, family, [wrongType]).options.length, 1);
    });
  }
  test(`${locale}/image routes: document/OCR and image-operation sources retain genuine pinned/deduplicated projection`, () => {
    const [now, old] = allInstances(locale);
    const pinned = asset("image", IDS[1], {display_name: "PINNED"}), listed = asset("image", IDS[0], {display_name: "LISTED"});
    for (const route of ["/documents/image-to-pdf", "/documents/ocr", "/image/resize"]) {
      const documentRoute = route.startsWith("/documents/");
      const raw = freeze({path: route, documentAssetReferenceReadState: "ready", imageOperationAssetReferenceReadState: "ready",
        documentAssetReferences: {image: documentRoute ? [listed, pinned] : [], pinned_image: documentRoute ? [pinned] : []},
        imageOperationAssetReferences: {items: documentRoute ? [] : [listed, pinned], pinned: documentRoute ? [] : [pinned]}});
      const fields = freeze([field("imageVaultAssets")]), values = freeze({source_id: IDS[0]});
      const html = now.render(fields, true, raw, values, "route-owned");
      assert.deepEqual(options(html).slice(1).map(option => [option.value, option.label]),
        [[IDS[1], "PINNED · PNG · 1.5 KB"], [IDS[0], "LISTED · PNG · 1.5 KB"]]);
      assert.equal(html, old.render(fields, true, raw, values, "route-owned"));
    }
  });
  test(`${locale}/unrelated: text checkbox package image-tier video-tier and static options retain full BASE HTML`, () => {
    const [now, old] = allInstances(locale);
    const fields = freeze([
      {name: "brief", label: "SYNTHETIC BRIEF", type: "text", placeholder: CUSTOMER, required: true, maxLength: 80, help: "HELP"},
      {name: "consent", label: "CONSENT", type: "checkbox", checkboxLabel: CUSTOMER, required: true},
      field("packages", {name: "package"}), field("imageTiers", {name: "image"}),
      field("videoTiers", {name: "video"}), {name: "static", label: "STATIC", control: "select", options: [["raw", CUSTOMER], ["other", "OTHER"]]}
    ]);
    const raw = freeze({pricingCatalog: {image_tiers: [{code: "image-code", label: CUSTOMER}, {code: "fallback-code"}, {}],
      video_tiers: [{code: "video-code", label: CUSTOMER}]},
      packageCatalog: {monthly: [{code: "monthly", label: CUSTOMER}, {code: "manual", label: "EXCLUDED", manual: true}],
        combos: [{code: "combo", label: CUSTOMER}, {code: "fallback-combo"}]}});
    const values = freeze({brief: CUSTOMER, consent: "true", package: "combo", image: "image-code", video: "video-code", static: "raw"});
    const html = now.render(fields, true, raw, values, "untouched");
    assert.equal(html, old.render(fields, true, raw, values, "untouched"));
    assert.ok(html.includes(" checked") && html.includes("maxlength=\"80\""));
    assert.ok(!html.includes('value="manual"'));
    assert.ok(html.includes(escape(CUSTOMER)));
  });
  test(`${locale}/markup: stripping only approved missing-name/suffix option text leaves complete BASE HTML identical`, () => {
    const [now, old] = allInstances(locale);
    const fields = freeze(TARGETS.map((family, index) => field(family, {name: "selected_" + index})));
    const raw = freeze({projects: [row("projects", "")], memoryNotes: [row("memoryNotes", "", IDS[1])],
      voiceProfiles: [row("voiceProfiles", "", IDS[2], {is_default: true}), row("voiceProfiles", CUSTOMER, IDS[3], {is_default: true})]});
    const values = freeze({selected_0: IDS[0], selected_1: IDS[1], selected_2: IDS[2]});
    const mask = html => html.replace(/(<option value="([^"]*)"[^>]*>)([\s\S]*?)(<\/option>)/g,
      (all, open, value, text, close) => IDS.slice(0, 4).includes(value) ? open + "[APPROVED_OPTION_COPY]" + close : all);
    assert.equal(mask(now.render(fields, true, raw, values, "stable")), mask(old.render(fields, true, raw, values, "stable")));
  });
}

for (const family of TARGETS) {
  test(`${family}/same-VM: locale changes recompute fallback and default suffix without cached labels`, () => {
    const instance = runtime(physical, "vi");
    const rows = [row(family, "", IDS[0], family === "voiceProfiles" ? {is_default: true} : {})];
    for (const locale of ["vi", "en", "zh", "vi"]) {
      instance.setLocale(locale); assert.equal(instance.currentLocale(), locale);
      const result = rendered(instance, family, rows);
      assert.equal(result.options[1].label, COPY[locale][family] + (family === "voiceProfiles" ? COPY[locale].suffix : ""));
    }
  });
  test(`${family}/missing-translator: unchanged uiText boundary falls back to VI, including default suffix`, () => {
    const instance = runtime(physical, "en");
    instance.missingTranslator(true);
    const result = rendered(instance, family, [row(family, "", IDS[0], family === "voiceProfiles" ? {is_default: true} : {})]);
    assert.equal(result.options[1].label, COPY.vi[family] + (family === "voiceProfiles" ? COPY.vi.suffix : ""));
    instance.missingTranslator(false);
    assert.equal(rendered(instance, family, [row(family, "")]).options[1].label, COPY.en[family]);
  });
}
test("reachable names: truthy whitespace in project/note/voice is not newly trimmed; empty field list remains empty", () => {
  const instance = runtime(physical, "zh");
  for (const family of TARGETS) {
    const result = rendered(instance, family, [row(family, "   ")]);
    assert.equal(result.options[1].label, "   ");
  }
  assert.equal(instance.render([], true, freeze({}), freeze({})), "");
  assert.equal(instance.render(null, false, freeze({}), freeze({})), "");
});
