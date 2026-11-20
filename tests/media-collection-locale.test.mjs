import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {BASE, IDS, CUSTOMER, OLD_RIGHTS, sources, runtime, context, collection, plain, freeze, hash} from "./helpers/media-collection-locale-runtime.mjs";
import {mediaReadFeedbackHistoricalSnapshot} from "./helpers/media-read-feedback-snapshot.mjs";

const reviewedRaw = fs.readFileSync(new URL("./fixtures/media-collection-locale-reviewed.json", import.meta.url));
assert.equal(hash(reviewedRaw), "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515");
const COPY = JSON.parse(reviewedRaw).copyRows, CURRENT = sources(), ORIGINAL = sources({baseline: true});
const LOCALES = ["vi", "en", "zh"];
const D = freeze({
  vi: {context: "Sử dụng chung", rights: "Tôi xác nhận có quyền sử dụng các tệp và yêu cầu trong bộ sưu tập này."},
  en: {context: "General use", rights: "I confirm that I have the right to use the files and brief in this collection."},
  zh: {context: "通用用途", rights: "我确认有权使用此合集中的文件和创作需求。"}
});
const PAG = freeze({
  vi: {range: "Đang hiển thị {from}–{to} {label}", empty: "Không có {label} ở trang này",
    previous: "← Trang trước", next: "Trang sau →", aria: "Phân trang {label}", label: "bộ sưu tập âm thanh"},
  en: {range: "Showing {from}–{to} {label}", empty: "No {label} on this page",
    previous: "← Previous", next: "Next →", aria: "{label} pagination", label: "audio collection"},
  zh: {range: "正在显示第 {from}–{to} 个{label}", empty: "此页没有{label}",
    previous: "← 上一页", next: "下一页 →", aria: "{label}分页", label: "音频合集"}
});
const FALSY = [["undefined", undefined], ["null", null], ["zero", 0], ["false", false], ["empty", ""]];
const TRUTHY = [["customer", CUSTOMER], ["whitespace", "   \t "], ["general", "general"],
  ["exact old Vietnamese rights", OLD_RIGHTS], ["Facebook TikTok", "Facebook TikTok"],
  ["number", 42], ["boolean", true], ["object", {owner: "literal"}], ["array", ["TikTok", "Facebook"]]];
const E = value => String(value).replace(/[&<>'"]/g, character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;",
  "'": "&#39;", '"': "&quot;"}[character]));
const interpolate = (text, params) => text.replace(/\{([^}]+)\}/g, (whole, key) => String(params[key] ?? whole));
const listing = pagination => ({pagination: {offset: 0, returned: 2, previous_offset: null,
  has_more: true, next_offset: 50, ...pagination}});
const PAGES = [
  ["first next50", listing({}), null, 50],
  ["previous0 only", listing({offset: 50, previous_offset: 0, next_offset: null, has_more: false}), 0, null],
  ["both50and150", listing({offset: 100, returned: 50, previous_offset: 50, next_offset: 150}), 50, 150],
  ["empty previous0", listing({offset: 50, returned: 0, previous_offset: 0, has_more: false, next_offset: null}), 0, null]
];
function expectedPagination(locale, value, label, route = "/media-workspace") {
  const p = value.pagination, copy = PAG[locale];
  const previous = Number.isInteger(p.previous_offset) && p.previous_offset >= 0 ? p.previous_offset : null;
  const next = p.has_more === true && Number.isInteger(p.next_offset) && p.next_offset > p.offset ? p.next_offset : null;
  if (previous === null && next === null) return "";
  const params = {from: p.offset + 1, to: p.offset + p.returned, label};
  const button = (offset, text) => '<button class="portal-button portal-button--quiet" type="button" data-portal-action="media-workspace-page" data-portal-route="' + E(route) + '" data-media-collection-offset="' + offset + '">' + E(text) + "</button>";
  return '<nav class="portal-media-pagination" aria-label="' + E(interpolate(copy.aria, params)) + '"><span>'
    + E(interpolate(p.returned ? copy.range : copy.empty, params)) + "</span><div>"
    + (previous === null ? "" : button(previous, copy.previous)) + (next === null ? "" : button(next, copy.next))
    + "</div></nav>";
}
function contracts(html) {
  return [...html.matchAll(/<(form|input|select|textarea|button|option|a|nav)\b([^>]*)>/g)].map(match => {
    const attributes = Object.fromEntries([...match[2].matchAll(/([^\s=<>]+)(?:="([^"]*)")?/g)]
      .map(value => [value[1], value[2] ?? true]));
    const keep = {};
    for (const [key, value] of Object.entries(attributes)) {
      if (/^data-/.test(key) || ["name", "id", "type", "required", "disabled", "minlength", "maxlength",
        "min", "max", "step", "inputmode", "multiple", "selected", "novalidate", "href", "value"].includes(key)) keep[key] = value;
    }
    if (["use_context", "rights_note"].includes(attributes.name)) delete keep.value;
    if (match[1] === "form") keep.class = attributes.class;
    return JSON.stringify({tag: match[1], attributes: Object.fromEntries(Object.entries(keep).sort())});
  }).sort();
}
function formContracts(fields) {
  return plain(fields).map(field => Object.fromEntries(Object.entries(field)
    .filter(([key]) => !["label", "placeholder", "help", "emptyLabel", "options"].includes(key))
    .concat(field.options ? [["optionValues", field.options.map(option => option[0])]] : [])));
}
function openDetail(rt, row) {
  const route = "/media-workspace/" + row.id;
  return rt.call("renderMediaWorkspaceDetail", rt.page(route), context({row, overrides: {path: route}}));
}

test("full BASE/current bundles have one exposure and no substituted production functions or side effects", () => {
  assert.equal(BASE, "4080b879ad8d6ded081aa47313bf9cac67121f0b");
  for (const source of [ORIGINAL, CURRENT]) {
    const rt = runtime(source);
    assert.equal(rt.binding.exposureCount, 1); assert.equal(rt.binding.replacedProductionFunctions, 0);
    assert.equal(rt.binding.executedPortalBytes - rt.binding.physicalPortalBytes, rt.binding.exposureBytes);
    assert.equal(rt.binding.hashes.portal, source.hashes.portal);
    assert.deepEqual(rt.attempts(), []);
  }
});

for (const locale of LOCALES) {
  test(`${locale}: new 2 defaults and 5 pagination catalogue values are literal, equal-keyset and deeply frozen`, () => {
    const rt = runtime(CURRENT, locale), m = rt.messages[locale];
    assert.ok(Object.isFrozen(rt.messages)); for (const name of LOCALES) assert.ok(Object.isFrozen(rt.messages[name]));
    assert.deepEqual(Object.keys(rt.messages.vi).sort(), Object.keys(rt.messages.en).sort());
    assert.deepEqual(Object.keys(rt.messages.vi).sort(), Object.keys(rt.messages.zh).sort());
    assert.equal(m["audioWorkspace.defaults.context"], D[locale].context);
    assert.equal(m["audioWorkspace.defaults.rights"], D[locale].rights);
    for (const key of ["range", "empty", "previous", "next", "aria"]) assert.equal(m["audioWorkspace.pagination." + key], PAG[locale][key]);
  });
  test(`${locale}: exact 38-row reviewed catalogue target and all unrelated BASE messages are protected`, () => {
    // Historical PR782 catalogue comparison only; the other93 cases still
    // execute current physical renderer/i18n without a source projection.
    const now = Object.fromEntries(mediaReadFeedbackHistoricalSnapshot(
      Object.entries(runtime(CURRENT, locale).messages[locale]), locale));
    const before = runtime(ORIGINAL, locale).messages[locale];
    assert.equal(COPY.length, 38); assert.equal(new Set(COPY.map(row => row[0])).size, 38);
    const allow = new Set(COPY.map(row => "audioWorkspace." + row[0]));
    for (const row of COPY) assert.equal(now["audioWorkspace." + row[0]], row[LOCALES.indexOf(locale) + 1]);
    for (const [key, value] of Object.entries(before)) if (!allow.has(key)) assert.equal(now[key], value, key);
    assert.deepEqual(Object.keys(now).filter(key => !Object.hasOwn(before, key)).sort(),
      ["defaults.context", "defaults.rights", "pagination.range", "pagination.empty", "pagination.previous", "pagination.next", "pagination.aria"]
        .map(key => "audioWorkspace." + key).sort());
    assert.ok(Object.keys(before).every(key => Object.hasOwn(now, key)), "No BASE key removed");
  });
  for (const [name, value] of FALSY) test(`${locale}: ${name} defaults at values/context, values/rights, cards/context and real detail/context`, () => {
    const rt = runtime(CURRENT, locale), row = collection({use_context: value, rights_note: value});
    const values = plain(rt.call("mediaCollectionValues", row));
    assert.equal(values.use_context, D[locale].context); assert.equal(values.rights_note, D[locale].rights);
    assert.ok(rt.call("renderMediaCollectionCards", [row], "/media-workspace").includes(" · " + E(D[locale].context) + "</span>"));
    assert.ok(openDetail(rt, row).includes(" · " + E(D[locale].context) + "</span>"));
  });
  for (const [name, value] of TRUTHY) test(`${locale}: truthy ${name} preserves old String semantics without translation or mutation`, () => {
    const rt = runtime(CURRENT, locale), row = collection({use_context: value, rights_note: value});
    const values = plain(rt.call("mediaCollectionValues", row));
    assert.equal(values.use_context, String(value)); assert.equal(values.rights_note, String(value));
    assert.ok(rt.call("renderMediaCollectionCards", [row], "/media-workspace").includes(" · " + E(String(value)) + "</span>"));
    assert.ok(openDetail(rt, row).includes(" · " + E(String(value)) + "</span>"));
  });
  test(`${locale}: all other returned values, mode selection, tag spacing and project UUID remain hand-derived`, () => {
    const rt = runtime(CURRENT, locale);
    const input = {title: 19, description: false, creative_brief: CUSTOMER, prompt_mode: "lyrics",
      tags: [" first ", "", "TikTok", 3], project_id: IDS[1], use_context: "Customer usage", rights_note: OLD_RIGHTS};
    assert.deepEqual(plain(rt.call("mediaCollectionValues", input)), {title: "19", description: "",
      creative_brief: CUSTOMER, prompt_mode: "lyrics", tags: " first , TikTok", project_id: IDS[1],
      use_context: "Customer usage", rights_note: OLD_RIGHTS});
    for (const mode of ["background", "lyrics", "script", "melody", "custom"]) {
      assert.equal(rt.call("mediaCollectionValues", {prompt_mode: mode}).prompt_mode, mode);
    }
    for (const mode of ["Lyrics", " unknown ", 7, null]) assert.equal(rt.call("mediaCollectionValues", {prompt_mode: mode}).prompt_mode, "background");
    assert.deepEqual(plain(rt.call("mediaCollectionValues", {tags: Array.from({length: 20}, (_, i) => "t" + i)})).tags,
      Array.from({length: 16}, (_, i) => "t" + i).join(", "));
  });
  test(`${locale}: frozen customer HTML is escaped in real cards/detail and never becomes markup`, () => {
    const rt = runtime(CURRENT, locale), row = freeze(collection({use_context: CUSTOMER, rights_note: CUSTOMER}));
    const before = JSON.stringify(row);
    for (const html of [rt.call("renderMediaCollectionCards", [row], "/media-workspace"), openDetail(rt, row)]) {
      assert.ok(html.includes(E(CUSTOMER))); assert.ok(!html.includes("<img src=x"));
      assert.ok(html.includes("Facebook TikTok")); assert.ok(html.includes("onerror=&quot;literal&quot;"));
    }
    assert.equal(JSON.stringify(row), before); assert.deepEqual(rt.attempts(), []);
  });
  for (const [name, value, previous, next] of PAGES) test(`${locale}: collection pagination ${name} translates exact range/empty/buttons/aria and preserves offsets`, () => {
    const rt = runtime(CURRENT, locale), label = "QA <label> &";
    const html = rt.call("renderMemoryPagination", value, label, "media-workspace-page", "/media-workspace",
      "data-media-collection-offset", "portal-media-pagination");
    assert.equal(html, expectedPagination(locale, value, label));
    const expectedOffsets = [previous, next].filter(offset => offset !== null).map(String);
    assert.deepEqual([...html.matchAll(/data-media-collection-offset="(\d+)"/g)].map(match => match[1]), expectedOffsets);
    const old = runtime(ORIGINAL, locale).call("renderMemoryPagination", value, label, "media-workspace-page",
      "/media-workspace", "data-media-collection-offset", "portal-media-pagination");
    assert.deepEqual(contracts(html), contracts(old), "Native type/action/route/offset controls unchanged");
  });
  test(`${locale}: pagination route/default wrapper and hostile label use literal localized expectations`, () => {
    const rt = runtime(CURRENT, locale), value = listing({});
    assert.equal(rt.call("renderMediaWorkspacePagination", value), expectedPagination(locale, value, PAG[locale].label));
    assert.equal(rt.call("renderMediaWorkspacePagination", value, "/audio-hub"),
      expectedPagination(locale, value, PAG[locale].label, "/audio-hub"));
    const route = '/media-workspace?literal="<tag>"&x=1';
    assert.equal(rt.call("renderMemoryPagination", value, CUSTOMER, "media-workspace-page", route,
      "data-media-collection-offset", "portal-media-pagination"), expectedPagination(locale, value, CUSTOMER, route));
  });
  test(`${locale}: invalid or absent paging controls do not create a nav`, () => {
    const rt = runtime(CURRENT, locale);
    for (const value of [null, {}, listing({previous_offset: -1, next_offset: 0}),
      listing({previous_offset: "0", next_offset: "50"}), listing({has_more: false, previous_offset: null})]) {
      assert.equal(rt.call("renderMemoryPagination", value, "QA", "media-workspace-page", "/media-workspace",
        "data-media-collection-offset", "portal-media-pagination"), "");
    }
  });
  test(`${locale}: every other class/action including media-audio-page retains complete BASE pagination HTML`, () => {
    const now = runtime(CURRENT, locale), before = runtime(ORIGINAL, locale);
    const consumers = [["portal-media-pagination", "media-audio-page"], ["portal-media-pagination", "other-action"],
      ["portal-memory-pagination", "media-workspace-page"], ["portal-music-library-pagination", "music-library-page"],
      ["portal-prompt-library-pagination", "prompt-library-page"], ["custom-pagination", "media-workspace-page"],
      ["portal-media-pagination extra", "media-workspace-page"], [undefined, "memory-note-page"]];
    for (const [className, action] of consumers) for (const [, value] of PAGES) {
      const args = [value, CUSTOMER, action, "/protected-route", "data-protected-offset", className];
      assert.equal(now.call("renderMemoryPagination", ...args), before.call("renderMemoryPagination", ...args));
    }
  });
  for (const canCreate of [true, false]) for (const route of ["/media-workspace", "/media-workspace/new"]) {
    test(`${locale}: cleanup ${route} create=${canCreate} removes only policy/layout/execution summary and retains controls, links, events and data`, () => {
      const now = runtime(CURRENT, locale), before = runtime(ORIGINAL, locale);
      const fixture = context({canCreate, overrides: {path: route,
        mediaWorkspaceSummary: {collections: {total: 1, active: 1}, items: {total: 0, favorites: 0},
          execution: {authoring: "QA_AUTHORING_TECH_STATUS", generation: "QA_PROVIDER_TECH_STATUS"}}}});
      const html = now.call("renderMediaWorkspace", now.page(route), fixture);
      const base = before.call("renderMediaWorkspace", before.page(route), fixture);
      assert.ok(!html.includes('class="portal-media-workspace-layout"'));
      assert.ok(!/<aside\b[^>]*portal-media-policy/.test(html)); assert.ok(!html.includes("portal-media-guarded-list"));
      for (const raw of ["QA_CANONICAL_PROVIDER_TECHNICAL_POLICY", "qa provider runtime guarded",
        "QA_AUTHORING_TECH_STATUS", "QA_PROVIDER_TECH_STATUS"]) assert.ok(!html.includes(raw), raw);
      assert.deepEqual(contracts(html), contracts(base), "Exact BASE form/filter/list/pagination/action/disabled/data contract counts");
      for (const href of ["/asset-vault", "/projects"]) {
        assert.equal([...html.matchAll(new RegExp('href="' + href + '"', "g"))].length,
          [...base.matchAll(new RegExp('href="' + href + '"', "g"))].length);
      }
      const createForm = html.match(/<form\b[^>]*data-portal-action="media-collection-create"[\s\S]*?<\/form>/)?.[0];
      assert.ok(createForm && /portal-inline-actions/.test(createForm));
      assert.ok(createForm.includes('href="/asset-vault"') && createForm.includes('href="/projects"'));
      assert.equal(/type="submit" disabled/.test(createForm), !canCreate);
      assert.ok(html.includes("v7 · 2026-11-20T09:01:02Z")); assert.ok(html.includes(E(CUSTOMER)));
      assert.ok(html.includes("/media-workspace/" + IDS[0]));
      assert.ok(now.body("renderMediaWorkspace").includes('badge(canCreate ? "ready" : "guarded")'));
    });
  }
  test(`${locale}: no-view permission remains fail-closed with no create/filter forms or customer metadata`, () => {
    const now = runtime(CURRENT, locale), before = runtime(ORIGINAL, locale), fixture = context({canView: false});
    const html = now.call("renderMediaWorkspace", now.page("/media-workspace"), fixture);
    const base = before.call("renderMediaWorkspace", before.page("/media-workspace"), fixture);
    assert.deepEqual(contracts(html), contracts(base));
    assert.ok(!html.includes('data-portal-action="media-collection-create"'));
    assert.ok(!html.includes('data-portal-action="media-workspace-filter"')); assert.ok(!html.includes(E(CUSTOMER)));
  });
  test(`${locale}: create/editor field names, requirements, lengths, option values and project source stay BASE-exact`, () => {
    const now = runtime(CURRENT, locale), before = runtime(ORIGINAL, locale);
    for (const name of ["mediaCollectionFormFields", "mediaCollectionShellFormFields"]) {
      const actual = now.call(name), old = before.call(name);
      assert.deepEqual(formContracts(actual), formContracts(old));
      assert.deepEqual(plain(actual).map(field => field.name),
        ["title", "creative_brief", "description", "prompt_mode", "use_context", "tags", "project_id", "rights_note"]);
      assert.deepEqual(formContracts(actual).find(field => field.name === "rights_note"),
        {name: "rights_note", required: true, minLength: 2, maxLength: 800});
    }
  });
}

test("same VM VI→EN→ZH→VI recomputes all four owned defaults without stale cached locale", () => {
  const rt = runtime(CURRENT, "vi");
  for (const locale of ["vi", "en", "zh", "vi"]) {
    rt.setLocale(locale); assert.equal(rt.currentLocale(), locale);
    const row = collection({use_context: "", rights_note: ""}), values = rt.call("mediaCollectionValues", row);
    assert.equal(values.use_context, D[locale].context); assert.equal(values.rights_note, D[locale].rights);
    assert.ok(rt.call("renderMediaCollectionCards", [row], "/media-workspace").includes(" · " + E(D[locale].context) + "</span>"));
    assert.ok(openDetail(rt, row).includes(" · " + E(D[locale].context) + "</span>"));
  }
});
test("missing translator defaults are Vietnamese at all four owned sites, never English or legacy general", () => {
  const rt = runtime(CURRENT, "en"); rt.missingTranslator();
  const row = collection({use_context: null, rights_note: null}), values = rt.call("mediaCollectionValues", row);
  assert.equal(values.use_context, D.vi.context); assert.equal(values.rights_note, D.vi.rights);
  for (const html of [rt.call("renderMediaCollectionCards", [row], "/media-workspace"), openDetail(rt, row)]) {
    assert.ok(html.includes(" · Sử dụng chung</span>")); assert.ok(!html.includes(" · general</span>"));
  }
  rt.missingTranslator(false); assert.equal(rt.call("mediaCollectionValues", row).use_context, "General use");
  assert.deepEqual(rt.attempts(), []);
});
