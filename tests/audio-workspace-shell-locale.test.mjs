import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");
const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");

function functionSource(name) {
  const start = portalSource.indexOf(`  function ${name}(`);
  assert.notEqual(start, -1, `Missing ${name}`);
  const end = portalSource.indexOf("\n  }", start) + 4;
  assert.ok(end > start, `Could not isolate ${name}`);
  return portalSource.slice(start, end);
}

const mediaStart = portalSource.indexOf("  const MEDIA_PROMPT_MODES");
const mediaEnd = portalSource.indexOf("\n  function mediaAudioOperationHandoffAsset", mediaStart);
assert.notEqual(mediaStart, -1, "Media shell block exists");
assert.notEqual(mediaEnd, -1, "Media shell block boundary exists");
const mediaShellSource = portalSource.slice(mediaStart, mediaEnd);

function textOf(html) {
  return html
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function createHarness(locale) {
  const ctx = {
    window: null,
    document: null,
    ICONS: { music: "music" },
    validProjectId: value => /^[0-9a-f-]{8,64}$/i.test(String(value || "")),
    validVaultAssetId: value => /^[0-9a-f-]{8,64}$/i.test(String(value || "")),
    memoryListingPagination: value => value && typeof value === "object" ? value : {},
    transientFormValues: () => ({}),
    vaultBytes: () => "1 KB",
    mediaCollectionTags: value => Array.isArray(value) ? value.map(String).slice(0, 16) : [],
    renderMemoryPagination: () => "<nav data-pagination>1</nav>",
    renderEmpty: (title, body) => `<section data-empty><h2>${title}</h2><p>${body}</p></section>`,
    badge: state => `<span data-badge="${state}">${state}</span>`,
    renderHero: () => "<header><h1>QA</h1></header>",
    renderFields: fields => fields.map((field) => {
      const options = Array.isArray(field.options)
        ? field.options.map(option => `<option value="${option[0]}">${option[1]}</option>`).join("")
        : "";
      return `<label><span>${field.label || ""}</span><input name="${field.name}" placeholder="${field.placeholder || ""}">${options}<small>${field.help || ""}</small></label>`;
    }).join("")
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  vm.runInContext([
    functionSource("portalI18n"),
    functionSource("uiText"),
    functionSource("audioWorkspaceText"),
    functionSource("safeText"),
    mediaShellSource
  ].join("\n"), ctx);
  return ctx;
}

const page = { path: "/media-workspace", routePath: "/media-workspace", title: "Audio", description: "Audio" };

function contextFor(locale) {
  const dynamic = {
    vi: { title: "Dữ liệu khách hàng", brief: "Yêu cầu do khách nhập", useContext: "bối cảnh riêng", policy: "Chính sách máy chủ riêng" },
    en: { title: "Customer data", brief: "Customer-authored brief", useContext: "customer context", policy: "Server-owned policy" },
    zh: { title: "客户数据", brief: "客户填写的需求", useContext: "客户上下文", policy: "服务器策略" }
  }[locale];
  return {
    locale,
    capabilities: { "media-workspace-view": true, "media-workspace-create": true },
    mediaWorkspaceSummary: { collections: { active: 2 }, items: { total: 3, favorites: 1 }, execution: { authoring: "ready", generation: "guarded" } },
    mediaWorkspaceListing: { filters: { q: "", tag: "", prompt_mode: "", state: "all" }, pagination: {} },
    mediaWorkspaceFilter: { q: "", tag: "", prompt_mode: "", state: "all" },
    mediaWorkspacePolicy: { policy: [dynamic.policy], guarded_capabilities: ["provider_library"] },
    mediaWorkspaceEvents: [{ action: "collection_created", revision: 2, created_at: "2026-10-15T10:00:00Z" }],
    mediaCollections: [{ id: "12345678-abcd", prompt_mode: "background", use_context: dynamic.useContext, title: dynamic.title, brief_excerpt: dynamic.brief, state: "active", revision: 2, updated_at: "2026-10-15T10:00:00Z", tags: ["customer-tag"], policy: { status: "guarded" } }]
  };
}

function assertLocalePurity(locale, text) {
  const dataRemoved = text
    .replace(/Dữ liệu khách hàng|Yêu cầu do khách nhập|bối cảnh riêng|Chính sách máy chủ riêng/g, "")
    .replace(/Customer data|Customer-authored brief|customer context|Server-owned policy/g, "")
    .replace(/客户数据|客户填写的需求|客户上下文|服务器策略/g, "")
    .replace(/2026-10-15T10:00:00Z|customer-tag|provider library|ready|guarded/g, "");
  if (locale === "vi") {
    assert.doesNotMatch(dataRemoved, /\b(?:collection|metadata|read-only|private|player|catalog|active|reference|signed|generic|audio|brief|policy|provider|generation|authoring|output|charge|Music|Background|Lyrics|Script|Melody|Custom)\b/i);
  } else if (locale === "en") {
    assert.doesNotMatch(dataRemoved, /[À-ỹĐđ]|\b(?:bộ sưu tập|âm thanh|đang|chưa|riêng tư|chỉ|mở|tìm|cập nhật|trạng thái|yêu cầu|chính sách|tài liệu|thao tác|soạn thảo|xử lý)\b/i);
  } else {
    const withoutNouns = dataRemoved.replace(/\b(?:Asset Vault|Telegram|Bot|CSRF|OTP|CVV|SFX|Web|AI|URL)\b/g, "");
    assert.doesNotMatch(withoutNouns, /[A-Za-z]{3,}/);
  }
}

test("R213-02 has one equal VI/EN/ZH audioWorkspace catalogue", () => {
  const ctx = createHarness("vi");
  const messages = ctx.TOANAASI18n.messages;
  const keysets = ["vi", "en", "zh"].map(locale => Object.keys(messages[locale]).filter(key => key.startsWith("audioWorkspace.")).sort());
  assert.ok(keysets[0].length >= 90, "Audio shell catalogue is populated");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});
for (const locale of ["vi", "en", "zh"]) {
  test(`Media Workspace shell renders clean ${locale} copy and preserves contracts`, () => {
    const ctx = createHarness(locale);
    const html = ctx.renderMediaWorkspace(page, contextFor(locale));
    const text = textOf(html);
    assertLocalePurity(locale, text);
    for (const contract of [
      'data-portal-action="media-collection-create"',
      'data-portal-action="media-workspace-filter"',
      'data-portal-action="media-workspace-refresh"',
      'data-portal-action="media-workspace-filter-clear"',
      'name="title"',
      'name="creative_brief"',
      'name="prompt_mode"',
      'name="project_id"',
      'name="rights_note"',
      'href="/asset-vault"',
      'href="/projects"',
      'Dữ liệu khách hàng|Customer data|客户数据'
    ]) {
      if (contract.includes("|")) continue;
      assert.match(html, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
    }
    assert.match(html, locale === "vi" ? /Tạo bộ sưu tập âm thanh/ : locale === "en" ? /Create audio collection/ : /创建音频合集/);
    assert.match(html, locale === "vi" ? /Tìm bộ sưu tập/ : locale === "en" ? /Search collections/ : /搜索合集/);
    assert.match(html, /Dữ liệu khách hàng|Customer data|客户数据/);
    assert.match(html, /Yêu cầu do khách nhập|Customer-authored brief|客户填写的需求/);
    assert.match(html, /2026-10-15T10:00:00Z/);
  });
}

test("R213-02 keeps canonical mode and role values", () => {
  assert.match(mediaShellSource, /const MEDIA_PROMPT_MODES = Object\.freeze\(\[/);
  assert.match(mediaShellSource, /\["background", "Nhạc nền"\]/);
  assert.match(mediaShellSource, /\["lyrics", "Bài hát có lời nguyên gốc"\]/);
  assert.match(mediaShellSource, /\[\["music", "Music"\], \["sfx", "SFX"\], \["reference", "Reference"\]\]/);
  assert.match(mediaShellSource, /data-portal-action="media-collection-create"/);
});
