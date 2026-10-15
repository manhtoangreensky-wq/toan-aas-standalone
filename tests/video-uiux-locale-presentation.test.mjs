import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const studioStart = portalSource.indexOf("  const VIDEO_STUDIO_FORMATS");
const studioEnd = portalSource.indexOf("\n  // Image Creative Studio", studioStart);
assert.ok(studioStart > 0 && studioEnd > studioStart, "Video Studio source boundary exists");
const studioSource = portalSource.slice(studioStart, studioEnd);
const hubStart = portalSource.indexOf("  function renderVideoHub");
const hubEnd = portalSource.indexOf("\n  function renderImageSuiteHub", hubStart);
assert.ok(hubStart > 0 && hubEnd > hubStart, "Video Hub source boundary exists");
const hubSource = portalSource.slice(hubStart, hubEnd);
const formStart = portalSource.indexOf("  function renderFormCard");
const formEnd = portalSource.indexOf("\n  const ADMIN_TAB_GROUPS", formStart);
assert.ok(formStart > 0 && formEnd > formStart, "Generic form source boundary exists");
const formSource = portalSource.slice(formStart, formEnd);

function textOf(html) {
  return String(html).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function createHarness(locale) {
  const ctx = {
    window: null,
    document: null,
    ICONS: { video: "video" },
    currentLocale: locale,
    validProjectId(value) {
      return /^[0-9a-f-]{8,64}$/i.test(String(value || ""));
    },
    safeText(value) {
      return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
    },
    uiText(key, fallback, params) {
      const value = ctx.TOANAASI18n.t(key, params);
      return typeof value === "string" && value ? value : fallback;
    },
    transientFormValues: () => ({}),
    renderHero: (page) => `<header><h1>${ctx.safeText(page.title || "Video")}</h1></header>`,
    badge: (state) => `<span data-badge="${ctx.safeText(state)}">${ctx.safeText(state)}</span>`,
    renderEmpty: (title, body) => `<section data-empty><h2>${ctx.safeText(title)}</h2><p>${ctx.safeText(body)}</p></section>`,
    renderFields(fields) {
      return fields.map((field) => {
        const label = field.labelKey ? ctx.uiText(field.labelKey, field.label) : field.label;
        const placeholder = field.placeholderKey ? ctx.uiText(field.placeholderKey, field.placeholder) : field.placeholder;
        const help = field.helpKey ? ctx.uiText(field.helpKey, field.help) : field.help;
        const options = Array.isArray(field.options) ? field.options.map((option) => `<option value="${ctx.safeText(option.value ?? option[0])}">${ctx.safeText(option.label ?? option[1])}</option>`).join("") : "";
        return `<label><span>${ctx.safeText(label || "")}</span><input name="${ctx.safeText(field.name)}" placeholder="${ctx.safeText(placeholder || "")}">${options}<small>${ctx.safeText(help || "")}</small></label>`;
      }).join("");
    }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  vm.runInContext(studioSource, ctx);
  return ctx;
}

function createHubHarness(locale) {
  const ctx = {
    window: null,
    document: null,
    ICONS: { video: "video" },
    currentLocale: locale,
    safeText(value) {
      return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
    },
    uiText(key, fallback, params) {
      const value = ctx.TOANAASI18n.t(key, params);
      return typeof value === "string" && value ? value : fallback;
    },
    renderHero: (page) => `<header><h1>${ctx.safeText(page.title || "Video")}</h1></header>`,
    portalIcon: (icon) => `<span data-icon="${ctx.safeText(icon)}"></span>`
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  vm.runInContext(hubSource, ctx);
  return ctx;
}

const page = { path: "/video-studio", routePath: "/video-studio", title: "Video Production Studio" };

function contextFor(locale) {
  const dynamic = {
    vi: { title: "Kế hoạch khách hàng", brief: "Mô tả do khách nhập", objective: "Giới thiệu sản phẩm", scene: "Mở đầu sản phẩm" },
    en: { title: "Customer plan", brief: "Customer-authored description", objective: "Introduce the product", scene: "Product opening" },
    zh: { title: "客户计划", brief: "客户填写的描述", objective: "介绍产品", scene: "产品开场" }
  }[locale];
  return {
    locale,
    capabilities: {
      "video-studio-view": true, "video-plan-create": true, "video-plan-update": true,
      "video-plan-lifecycle": true, "video-plan-restore-version": true,
      "video-scene-create": true, "video-scene-update": true, "video-scene-archive": true,
      "video-scene-restore": true, "video-scene-restore-version": true, "video-scene-reorder": true
    },
    videoStudioSummary: { plans: { total: 1, review: 1, approved: 0 } },
    videoPlans: [{ id: "12345678-abcd", title: dynamic.title, brief_excerpt: dynamic.brief, objective: dynamic.objective, format: "short_form", aspect_ratio: "9:16", target_duration_seconds: 30, scene_count: 1, state: "review", revision: 2, tags: ["customer-tag"] }],
    videoPlanDetail: {
      plan: { id: "12345678-abcd", title: dynamic.title, brief_excerpt: dynamic.brief, objective: dynamic.objective, format: "short_form", aspect_ratio: "9:16", target_duration_seconds: 30, state: "review", revision: 2, tags: ["customer-tag"] },
      scenes: [{ id: "87654321-abcd", title: dynamic.scene, scene_type: "hook", duration_seconds: 5, visual_direction: dynamic.brief, narration: dynamic.objective, state: "active", revision: 1, transition: "cut", tags: ["customer-tag"] }],
      versions: [{ revision: 2, title: dynamic.title, brief_excerpt: dynamic.brief, created_at: "2026-10-15T10:00:00Z" }],
      events: [{ action: "plan_created", revision: 1, created_at: "2026-10-15T10:00:00Z" }],
      estimate: { status: "ready", target_duration_seconds: 30, scene_duration_seconds: 5, delta_seconds: -25 }
    }
  };
}

test("R214 has one balanced VI/EN/ZH Video Studio catalogue", () => {
  const ctx = createHarness("vi");
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(ctx.TOANAASI18n.messages[locale]).filter((key) => key.startsWith("videoStudioUi.")).sort());
  assert.ok(keysets[0].length >= 150, "Video Studio catalogue is complete");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("R214 has one balanced VI/EN/ZH generic video-task catalogue", () => {
  const ctx = createHarness("vi");
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(ctx.TOANAASI18n.messages[locale]).filter((key) => key.startsWith("videoUi.")).sort());
  assert.ok(keysets[0].length >= 50, "generic video-task catalogue is complete");
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
  for (const key of ["videoUi.form.title", "videoUi.field.brief.label", "videoUi.field.scene_count.label", "videoUi.settings.title", "videoUi.output.title"]) {
    assert.ok(keysets[0].includes(key), `missing ${key}`);
  }
});

const staleHubEnglish = [
  "Video workspace", "Edit video", "Multi-scene video", "Open tool", "Check processing availability",
  "Before processing", "Plan and create AI video"
];

for (const locale of ["vi", "en", "zh"]) {
  test(`R214 Video Hub renders clean ${locale} chrome and keeps route contracts`, () => {
    const ctx = createHubHarness(locale);
    const pageTitle = locale === "vi" ? "Xưởng video" : locale === "en" ? "Video workspace" : "视频工作台";
    const html = ctx.renderVideoHub({ path: "/tools/video", routePath: "/tools/video", title: pageTitle }, {});
    for (const stale of staleHubEnglish) {
      if (locale !== "en") assert.doesNotMatch(html, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
    }
    const expectedTitle = locale === "vi" ? "Xưởng video" : locale === "en" ? "Video workspace" : "视频工作台";
    assert.match(html, new RegExp(expectedTitle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    for (const href of ["/video/finishing", "/video/frame-sequence", "/video/poster", "/video-studio", "/video/multiscene", "/video/product"]) {
      assert.match(html, new RegExp(`href=\\"${href.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}\\"`), href);
    }
    assert.match(html, /data-tool-state="ready"/);
    assert.match(html, /data-tool-state="guarded"/);
  });
}

test("R214 generic video forms keep the ordered brief-to-report flow", () => {
  assert.match(formSource, /const videoTask = route === "\/video\/create" \|\| route === "\/video\/multiscene"/);
  assert.match(formSource, /const coreNames = \["brief", "scene_count", "format"\]/);
  assert.match(formSource, /const steps = \["input", "plan", "quote", "confirm", "progress", "result", "recovery"\]/);
  assert.match(formSource, /data-video-flow-help/);
  assert.match(formSource, /data-video-optional-settings/);
  for (const contract of [
    'data-portal-form', 'data-portal-action="${safeText(formAction)}"', 'data-portal-route="${safeText(route)}"',
    'labelKey: `videoUi.field.${field.name}.label`'
  ]) assert.match(formSource, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
  for (const field of ['brief', 'scene_count', 'format']) {
    assert.match(portalSource, new RegExp(`name: "${field}"`), field);
  }
  assert.doesNotMatch(formSource, /provider_called|wallet_mutated|job_created/);
});

const staleFixedEnglish = [
  "Authoring boundary", "Plan editor", "Brief & review context", "Scene board", "Ordered scene board",
  "Version history", "Audit-safe feed", "Runtime estimate", "Media generation", "Media render", "Media delivery",
  "New production plan", "Plan library", "signed account", "owner check", "Self-review", "archive scene"
];

for (const locale of ["vi", "en", "zh"]) {
  test(`R214 Video Studio home/detail renders clean ${locale} chrome and preserves contracts`, () => {
    const ctx = createHarness(locale);
    const context = contextFor(locale);
    const home = ctx.renderVideoStudio(page, context);
    const detail = ctx.renderVideoStudioDetail({ ...page, path: "/video-studio/12345678-abcd", routePath: "/video-studio/12345678-abcd", recordId: "12345678-abcd" }, context);
    const combined = `${home}${detail}`;
    for (const stale of staleFixedEnglish) {
      if (locale !== "en") assert.doesNotMatch(combined, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
    }
    assert.match(combined, /Kế hoạch khách hàng|Customer plan|客户计划/);
    assert.match(combined, /Mô tả do khách nhập|Customer-authored description|客户填写的描述/);
    assert.match(combined, /2026-10-15T10:00:00Z/);
    for (const contract of [
      'data-portal-action="video-plan-create"', 'data-portal-action="video-studio-refresh"',
      'data-portal-action="video-plan-update"', 'data-portal-action="video-scene-create"',
      'data-portal-action="video-scene-update"', 'data-portal-action="video-scene-reorder"',
      'name="title"', 'name="brief"', 'name="target_duration_seconds"', 'name="format"', 'name="scene_type"',
      'href="/video-studio/12345678-abcd"'
    ]) assert.match(combined, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
    assert.match(textOf(home), locale === "vi" ? /Lập kế hoạch video/ : locale === "en" ? /Video planning/ : /视频规划/);
  });
}

test("R214 keeps canonical plan/scene values and does not expose output claims", () => {
  assert.match(studioSource, /data-portal-action="video-plan-create"/);
  assert.match(studioSource, /data-portal-action="video-scene-create"/);
  assert.match(studioSource, /data-video-plan-revision=/);
  assert.match(studioSource, /VIDEO_STUDIO_FORMATS/);
  assert.match(studioSource, /VIDEO_STUDIO_SCENE_TYPES/);
  assert.doesNotMatch(studioSource, /provider_called|wallet_mutated|job_created/);
});
