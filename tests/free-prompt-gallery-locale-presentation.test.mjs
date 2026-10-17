import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");

const helperStart = portalSource.indexOf("  function freePromptGalleryText(key, fallback, params)");
const helperEnd = portalSource.indexOf("\n  // Prompt authoring surfaces", helperStart);
const normalizeStart = portalSource.indexOf("  const FREE_PROMPT_GALLERY_BOUNDARY_FIELDS");
const normalizeEnd = portalSource.indexOf("\n  const PUBLISH_REVIEW_PACK_BOUNDARY_FIELDS", normalizeStart);
const renderStart = portalSource.indexOf("  function freePromptGalleryCatalogState(context)");
const renderEnd = portalSource.indexOf("\n  const VIETQR_BANKS", renderStart);

assert.notEqual(helperStart, -1, "Free Prompt Gallery UI helper exists");
assert.notEqual(helperEnd, -1, "Free Prompt Gallery UI helper boundary exists");
assert.notEqual(normalizeStart, -1, "Free Prompt Gallery normalizers exist");
assert.notEqual(normalizeEnd, -1, "Free Prompt Gallery normalizer boundary exists");
assert.notEqual(renderStart, -1, "Free Prompt Gallery renderers exist");
assert.notEqual(renderEnd, -1, "Free Prompt Gallery renderer boundary exists");

const gallerySource = portalSource.slice(renderStart, renderEnd);
const legacyFixedEnglish = [
  "Signed Web-only · read-only snapshot",
  "Snapshot catalog",
  "Read-only results",
  "Prompt detail",
  "Static prompt seed",
  "Memory Center riêng tư",
  "Execution boundary",
  "Provider / Bot / bridge",
  "Job / wallet / PayOS",
  "Asset / publish / delivery",
  "Prompt seed"
];

function createHarness(locale) {
  const ctx = { window: null, document: null };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  ctx.uiText = (key, fallback, params) => {
    const translated = ctx.TOANAASI18n.t(key, params);
    return typeof translated === "string" && translated ? translated : fallback;
  };
  const support = [
    portalSource.slice(helperStart, helperEnd),
    portalSource.slice(normalizeStart, normalizeEnd),
    gallerySource
  ].join("\n");
  ctx.renderHero = () => "<header><h1>Gallery</h1></header>";
  ctx.renderNotes = () => "";
  ctx.renderFields = (fields) => fields.map((field) => `<label>${field.label || ""}</label><input placeholder="${field.placeholder || ""}" title="${field.help || ""}">${(field.options || []).map((option) => `<option>${option[1]}</option>`).join("")}`).join("");
  ctx.renderEmpty = (title, body) => `<section data-empty><h2>${title}</h2><p>${body}</p></section>`;
  ctx.badge = (state) => `<span data-badge="${state}">${state}</span>`;
  vm.runInContext(`
    function safeText(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }
  `, ctx);
  vm.runInContext(support, ctx);
  return ctx;
}

const item = {
  id: "coffee_launch_sample",
  category_id: "content",
  category_title: "Nội dung",
  industry_id: "retail",
  industry: "Bán lẻ",
  title: "Mở đầu sản phẩm",
  prompt: "Viết một mở đầu rõ ràng cho bộ pha cà phê.",
  goals: ["launch"],
  platforms: ["social"]
};

const boundary = {
  gallery_request_persisted: false,
  provider_called: false,
  bot_called: false,
  bridge_called: false,
  job_created: false,
  wallet_mutated: false,
  payment_started: false,
  asset_saved: false,
  publish_action_created: false,
  delivery_created: false
};

function contextFor(locale) {
  const localized = {
    vi: {
      categoryTitle: "Nội dung",
      industry: "Bán lẻ",
      title: "Mở đầu sản phẩm",
      prompt: "Viết một mở đầu rõ ràng cho bộ pha cà phê.",
      description: "Danh mục đã được máy chủ xác minh.",
      copyInstruction: "Sao chép mẫu để tự rà soát.",
      noteCategory: "Ghi chú",
      notePriority: "normal"
    },
    en: {
      categoryTitle: "Content",
      industry: "Retail",
      title: "Product opening",
      prompt: "Write a clear opening for a coffee brewing kit.",
      description: "The catalogue has been verified by the server.",
      copyInstruction: "Copy the sample for self-review.",
      noteCategory: "Note",
      notePriority: "normal"
    },
    zh: {
      categoryTitle: "内容",
      industry: "零售",
      title: "产品开场",
      prompt: "为咖啡冲煮套装写一段清晰的开场。",
      description: "目录已由服务器确认。",
      copyInstruction: "复制样例以自行检查。",
      noteCategory: "笔记",
      notePriority: "normal"
    }
  }[locale];
  const localizedItem = {
    ...item,
    category_title: localized.categoryTitle,
    industry: localized.industry,
    title: localized.title,
    prompt: localized.prompt
  };
  return {
    locale,
    path: "/free-prompt-gallery",
    capabilities: { "free-prompt-gallery-view": true, "free-prompt-gallery-save": true },
    freePromptGalleryCatalog: {
      snapshot_version: "gallery-v1",
      description: localized.description,
      total_items: 2,
      categories: [{ id: "content", title: localized.categoryTitle, goals: ["launch"], platforms: ["social"], item_count: 1 }],
      industries: [{ id: "retail", title: localized.industry, item_count: 1 }]
    },
    freePromptGalleryListing: {
      filters: { category_id: "", industry_id: "", goal: "", platform: "", q: "" },
      pagination: { page: 1, page_size: 20, total_items: 1, total_pages: 1, has_next: false, has_previous: false },
      items: [localizedItem]
    },
    freePromptGalleryDetail: {
      snapshot_version: "gallery-v1",
      item: localizedItem,
      copy_instruction: localized.copyInstruction,
      boundaries: { execution: "web_native_static_prompt_gallery", snapshot_read_only: true, ...boundary }
    },
    freePromptGallerySaveResult: {
      note: { id: "123e4567-e89b-12d3-a456-426614174000", category: localized.noteCategory, priority: localized.notePriority, state: "active", revision: 1 },
      gallery: { prompt_id: item.id, snapshot_version: "gallery-v1" }
    }
  };
}

test("Free Prompt Gallery has an equal VI/EN/ZH fixed-chrome catalogue", () => {
  const ctx = createHarness("vi");
  const messages = ctx.TOANAASI18n.messages;
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("freePromptGallery.")).sort());
  assert.ok(keysets[0].length >= 35, "R213-01 catalogue is populated");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Free Prompt Gallery renderer uses locale chrome and keeps workflow contracts", () => {
  assert.doesNotMatch(gallerySource, /Signed Web-only|read-only snapshot|Execution \/ payment|Snapshot catalog|Read-only results|Prompt detail|Static prompt seed|Execution boundary/);
  assert.match(gallerySource, /freePromptGalleryText\(/);
  for (const contract of [
    'data-portal-action="free-prompt-gallery-filter"',
    'data-portal-action="free-prompt-gallery-refresh"',
    'data-portal-action="free-prompt-gallery-detail"',
    'data-portal-action="free-prompt-gallery-copy"',
    'data-portal-action="free-prompt-gallery-save"',
    'data-portal-action="free-prompt-gallery-page"',
    'data-free-prompt-gallery-id=',
    'data-copy-text='
  ]) assert.match(gallerySource, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
});

for (const locale of ["vi", "en", "zh"]) {
  test(`Free Prompt Gallery renders fixed chrome in clean ${locale}`, () => {
    const ctx = createHarness(locale);
    const html = ctx.renderFreePromptGallery({ routePath: "/free-prompt-gallery", title: "Thư viện" }, contextFor(locale));
    assert.match(html, /data-portal-action="free-prompt-gallery-filter"/);
    assert.match(html, /data-free-prompt-gallery-id="coffee_launch_sample"/);
    assert.match(html, /href="\/notes\/123e4567-e89b-12d3-a456-426614174000"/);
    if (locale !== "en") {
      for (const stale of legacyFixedEnglish) assert.doesNotMatch(html, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
    }
    if (locale === "vi") {
      assert.match(html, /Không gian Web riêng · chỉ đọc/);
      assert.match(html, /Danh mục bản chụp/);
      assert.match(html, /Tìm kiếm mẫu/);
      assert.match(html, /Tất cả nhóm/);
      assert.doesNotMatch(html, /\b(?:Sample|General|Previous|Next|Provider|Execution)\b/);
    } else if (locale === "en") {
      assert.match(html, /Private Web space · read-only/);
      assert.match(html, /Catalogue snapshot/);
      assert.match(html, /Search samples/);
      assert.match(html, /All groups/);
      assert.doesNotMatch(html, /\b(?:Không gian|Danh mục|Mẫu|Trước|Sau)\b/);
    } else {
      assert.match(html, /私有 Web 空间 · 只读/);
      assert.match(html, /目录快照/);
      assert.match(html, /搜索样例/);
      assert.match(html, /全部分组/);
      assert.doesNotMatch(html, /\b(?:Sample|General|Previous|Next|Provider|Execution)\b/);
    }
  });
}
