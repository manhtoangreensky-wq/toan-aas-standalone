import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(root, "static", "portal", "portal-i18n.js"), "utf8");
const registrySource = fs.readFileSync(path.join(root, "copyfast_registry.py"), "utf8");

function sourceBlock(startMarker, endMarker) {
  const start = portalSource.indexOf(startMarker);
  const end = portalSource.indexOf(endMarker, start);
  assert.ok(start >= 0 && end > start, `source block ${startMarker} must remain present`);
  return portalSource.slice(start, end);
}

const pageTitleSource = sourceBlock("function localizedPageTitle(", "\n  function documentTitle");
const pageDescriptionSource = sourceBlock("function localizedPageDescription(", "\n  function initials");
const moduleCardSource = sourceBlock("function moduleCard(", "\n  function fallbackCatalogGroup");

function loadI18n() {
  const document = { title: "", documentElement: { lang: "", setAttribute() {} } };
  const window = { document, navigator: { language: "vi" }, dispatchEvent() {}, CustomEvent: function CustomEvent() {} };
  const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp });
  vm.runInContext(i18nSource, context);
  return window.TOANAASI18n;
}

const i18n = loadI18n();
const localizedRoutes = [
  { route: "/image/upscale", key: "upscale" },
  { route: "/image/transform", key: "transform" },
  { route: "/music/sfx", key: "sfx" },
];
const accountRoutes = [
  ["dashboard", "/dashboard"],
  ["account", "/account"],
  ["interface_locale_navigator", "/account/interface-language"],
  ["account_activity", "/account/activity"],
  ["account_security", "/account/security"],
  ["workspace_care", "/account/workspace-care"],
  ["notes", "/notes"],
  ["reminders", "/reminders"],
  ["inbox", "/inbox"],
  ["automation", "/automation"],
  ["referrals", "/referrals"],
  ["rewards", "/rewards"],
  ["community", "/community"],
  ["guides", "/guides"],
];
const musicRoutes = [
  ["media_workspace", "/media-workspace"],
  ["audio_hub", "/audio-hub"],
  ["music_prompt_composer", "/media-workspace/music-prompt-composer"],
  ["music_direction_presets", "/media-workspace/music-directions"],
  ["sfx_cue_sheet", "/media-workspace/sfx-cue-sheet"],
  ["audio_asset_operations", "/audio/assets"],
  ["music_library", "/music/library"],
  ["sfx_library", "/music/sfx-library"],
  ["music_background", "/music/ai"],
  ["music_song", "/music/song"],
  ["music_sfx", "/music/sfx"],
  ["music_upload", "/music/upload"],
];
const voiceRoutes = [
  ["voice_studio", "/voice-studio", "customerVoiceStudio.page.title", "customerVoiceStudio.page.description"],
  ["voice_direction_composer", "/voice-studio/direction-composer", "customerVoiceStudio.composer.page.title", "customerVoiceStudio.composer.page.description"],
  ["voice_tts", "/voice/create", "featureCatalog.entry.voice_tts.title", "featureCatalog.entry.voice_tts.description"],
  ["voice_clone", "/voice/clone", "voiceUi.tool.clone.title", "voiceUi.tool.clone.description"],
  ["voice_saved_tts", "/voice/saved", "voiceUi.tool.saved.title", "voiceUi.tool.saved.description"],
  ["voice_vault", "/voice", "voiceUi.hub.title", "voiceUi.hub.description"],
  ["voice_preview", "/voice/preview", "voiceUi.tool.preview.title", "voiceUi.tool.preview.description"],
  ["voice_outputs", "/voice/outputs", "voiceUi.tool.outputs.title", "voiceUi.tool.outputs.description"],
];
const subtitleRoutes = [
  ["subtitle_studio", "/subtitle-studio"],
  ["subtitle_asset_operations", "/subtitle/assets"],
  ["subtitle_asr", "/subtitle"],
  ["subtitle_create", "/subtitle/create"],
  ["subtitle_translate", "/translate"],
  ["video_dub", "/dubbing"],
  ["asr", "/asr"],
  ["subtitle_formats", "/subtitle/formats"],
];
const imageRoutes = [
  ["image_studio", "/image-studio", "featureCatalog.entry.image_studio.title", "featureCatalog.entry.image_studio.description"],
  ["image_hub", "/image-hub", "featureCatalog.entry.image_hub.title", "featureCatalog.entry.image_hub.description"],
  ["quick_image_planner", "/image/quick-planner", "featureCatalog.entry.quick_image_planner.title", "featureCatalog.entry.quick_image_planner.description"],
  ["image_prompt_composer", "/image/prompt-composer", "featureCatalog.entry.image_prompt_composer.title", "featureCatalog.entry.image_prompt_composer.description"],
  ["image_create", "/image/create", "imageUi.page.title", "imageUi.page.description"],
  ["image_edit", "/image/edit", "featureCatalog.entry.image_edit.title", "featureCatalog.entry.image_edit.description"],
  ["image_resize", "/image/resize", "featureCatalog.entry.image_resize.title", "featureCatalog.entry.image_resize.description"],
  ["image_brand_overlay", "/image/brand-overlay", "featureCatalog.entry.image_brand_overlay.title", "featureCatalog.entry.image_brand_overlay.description"],
  ["image_storyboard_grid", "/image/storyboard-grid", "featureCatalog.entry.image_storyboard_grid.title", "featureCatalog.entry.image_storyboard_grid.description"],
  ["image_upscale", "/image/upscale", "mediaOperation.upscale.page.title", "mediaOperation.upscale.page.description"],
  ["image_transform", "/image/transform", "mediaOperation.transform.page.title", "mediaOperation.transform.page.description"],
  ["image_remove_background", "/image/remove-background", "featureCatalog.entry.image_remove_background.title", "featureCatalog.entry.image_remove_background.description"],
  ["image_history", "/image/history", "featureCatalog.entry.image_history.title", "featureCatalog.entry.image_history.description"],
];
const documentRoutes = [
  ["documents", "/documents"],
  ["documents_pdf", "/documents/pdf"],
  ["documents_ocr", "/documents/ocr"],
  ["documents_pdf_ocr", "/documents/pdf-ocr"],
  ["documents_pdf_ocr_word", "/documents/pdf-ocr-to-word"],
  ["documents_merge", "/documents/merge"],
  ["documents_split", "/documents/split"],
  ["documents_compress", "/documents/compress"],
  ["documents_image_to_pdf", "/documents/image-to-pdf"],
  ["documents_pdf_to_images", "/documents/pdf-to-images"],
  ["documents_pdf_to_word", "/documents/pdf-to-word"],
  ["documents_translate", "/documents/translate"],
];
const contentRoutes = [
  ["feature_catalog", "/features"],
  ["projects", "/projects"],
  ["project_packages", "/project-packages"],
  ["workspace_drafts", "/workspace"],
  ["workspace_menu", "/workspace-menu"],
  ["chat", "/chat"],
  ["analytics_workspace", "/analytics"],
  ["workboard", "/workboard"],
  ["campaign_planner", "/campaigns"],
  ["prompt_studio", "/prompt-studio"],
  ["prompt_library", "/prompt-library"],
  ["free_prompt_gallery", "/free-prompt-gallery"],
  ["content_studio", "/content-studio"],
  ["channel_strategy", "/content/channel-strategy"],
  ["content_prompt_pack", "/content/prompt-pack"],
  ["publish_review_pack", "/content/publish-review"],
  ["contextual_ad_prompt", "/content/contextual-prompt"],
  ["trend_research", "/trend-research"],
  ["media_factory", "/media-factory"],
  ["creative_flow", "/creative-flow"],
  ["source_rights_guide", "/guides/source-rights"],
  ["caption", "/content/caption"],
  ["hashtag", "/content/hashtag"],
  ["hook", "/content/hook"],
  ["script", "/content/script"],
  ["storyboard", "/content/storyboard"],
  ["content_pack", "/content/pack"],
  ["growth_ai", "/growth/ai"],
  ["campaign_report", "/campaign/report"],
  ["tool_directory", "/tools"],
];

function renderModuleCard(locale, route, catalogMode, keyOverride = "") {
  i18n.setLocale(locale, { emit: false });
  const page = {
    path: route,
    routePath: route,
    access: "member",
    status: "ready",
    icon: "image",
    title: "Trang dự phòng tiếng Việt",
    description: "Mô tả dự phòng tiếng Việt.",
  };
  const sandbox = vm.createContext({
    uiText: (key, fallback, params) => i18n.t(key, params) || fallback,
    featureCatalogText: (key, fallback, params) => i18n.t(`featureCatalog.${key}`, params) || fallback,
    mediaOperationText: (key, fallback, params) => i18n.t(`mediaOperation.${key}`, params) || fallback,
    imageUiText: (key, fallback, params) => i18n.t(`imageUi.${key}`, params) || fallback,
    voiceUiText: (key, fallback, params) => i18n.t(`voiceUi.${key}`, params) || fallback,
    voiceStudioText: (key, fallback, params) => i18n.t(`customerVoiceStudio.${key}`, params) || fallback,
    displayPageTitle: (value) => value && value.title || "",
    normalizePath: (value) => String(value || "").split("?")[0],
    safeCatalogRoute: (value) => value,
    manifest: { [route]: page },
    ALLOWED_STATES: new Set(["ready", "guarded", "read_only"]),
    catalogEntryState: () => "read_only",
    renderEngineLabel: () => "",
    renderReadinessLabel: () => "",
    portalIcon: () => "",
    safeText: (value) => String(value ?? ""),
    badge: (state) => `<span>${state}</span>`,
    ICONS: { default: "image" },
    localizedNavigationLabel: (value) => value,
    featureFamilyForPath: () => null,
    ADMIN_DATA_VIEW_ROUTE_KEYS: {},
    ADMIN_ERP_ROUTE_I18N: {},
  });
  vm.runInContext(`${pageTitleSource}\n${pageDescriptionSource}\n${moduleCardSource}; globalThis.render = moduleCard;`, sandbox);
  return sandbox.render({
    key: keyOverride || `catalog_${route.replaceAll("/", "_")}`,
    route,
    title: "Registry title that must not override route copy",
    description: "Registry description that must not override route copy",
    availability: "available",
  }, {}, "Open", catalogMode ? { showEngineLabel: true } : {});
}

test("catalog cards use translated destination-page copy for localized image and SFX routes", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const { route, key } of localizedRoutes) {
      const html = renderModuleCard(locale, route, true);
      const title = i18n.t(`mediaOperation.${key}.page.title`);
      const description = i18n.t(`mediaOperation.${key}.page.description`);
      assert.ok(title && description, `${locale}${route} route copy must exist`);
      assert.ok(html.includes(title), `${locale}${route} card must use the localized title`);
      assert.ok(html.includes(description), `${locale}${route} card must use the localized description`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("module cards outside feature-catalog mode keep their existing registry copy", () => {
  const html = renderModuleCard("vi", "/image/upscale", false);
  assert.ok(html.includes("Registry title that must not override route copy"));
  assert.ok(html.includes("Registry description that must not override route copy"));
});

test("all account-group catalog cards use the explicit vi/en/zh copy mapping", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route] of accountRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const title = i18n.t(`featureCatalog.entry.${key}.title`);
      const description = i18n.t(`featureCatalog.entry.${key}.description`);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must use its locale mapping`);
      assert.ok(html.includes(description), `${locale}.${key} card description must use its locale mapping`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("account-group locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"account"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(accountRoutes.map(([key]) => key).sort(), registeredKeys);
});

test("account registry group contains fourteen unique locale-mapped keys", () => {
  assert.equal(accountRoutes.length, 14);
  assert.equal(new Set(accountRoutes.map(([key]) => key)).size, 14);
});

test("music-group catalog cards use their locale copy or the translated route copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route] of musicRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const titleKey = key === "music_sfx" ? "mediaOperation.sfx.page.title" : `featureCatalog.entry.${key}.title`;
      const descriptionKey = key === "music_sfx" ? "mediaOperation.sfx.page.description" : `featureCatalog.entry.${key}.description`;
      const title = i18n.t(titleKey);
      const description = i18n.t(descriptionKey);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must be localized`);
      assert.ok(html.includes(description), `${locale}.${key} card description must be localized`);
    }
  }
});

test("music-group locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"music"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(musicRoutes.map(([key]) => key).sort(), registeredKeys);
});

test("all voice-group catalog cards use their translated route copy or explicit TTS copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route, titleKey, descriptionKey] of voiceRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const title = i18n.t(titleKey);
      const description = i18n.t(descriptionKey);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must use its locale copy`);
      assert.ok(html.includes(description), `${locale}.${key} card description must use its locale copy`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("voice-group locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"voice"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(voiceRoutes.map(([key]) => key).sort(), registeredKeys);
  assert.equal(voiceRoutes.length, 8);
  assert.equal(new Set(voiceRoutes.map(([key]) => key)).size, 8);
});

test("all subtitle and dubbing catalog cards use explicit vi/en/zh copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route] of subtitleRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const title = i18n.t(`featureCatalog.entry.${key}.title`);
      const description = i18n.t(`featureCatalog.entry.${key}.description`);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must use its locale copy`);
      assert.ok(html.includes(description), `${locale}.${key} card description must use its locale copy`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("subtitle and dubbing locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"subtitle"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(subtitleRoutes.map(([key]) => key).sort(), registeredKeys);
  assert.equal(subtitleRoutes.length, 8);
  assert.equal(new Set(subtitleRoutes.map(([key]) => key)).size, 8);
});

test("all image catalog cards use translated route copy or reviewed image-specific copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route, titleKey, descriptionKey] of imageRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const title = i18n.t(titleKey);
      const description = i18n.t(descriptionKey);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must use its locale copy`);
      assert.ok(html.includes(description), `${locale}.${key} card description must use its locale copy`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("image locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"image"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(imageRoutes.map(([key]) => key).sort(), registeredKeys);
  assert.equal(imageRoutes.length, 13);
  assert.equal(new Set(imageRoutes.map(([key]) => key)).size, 13);
});

test("all document catalog cards use explicit vi/en/zh copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route] of documentRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const title = i18n.t(`featureCatalog.entry.${key}.title`);
      const description = i18n.t(`featureCatalog.entry.${key}.description`);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card title must use its locale copy`);
      assert.ok(html.includes(description), `${locale}.${key} card description must use its locale copy`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("document locale map covers every current registry key", () => {
  const registeredKeys = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"documents"\s*,\s*"[^"]+"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(documentRoutes.map(([key]) => key).sort(), registeredKeys);
  assert.equal(documentRoutes.length, 12);
  assert.equal(new Set(documentRoutes.map(([key]) => key)).size, 12);
});

test("all content catalog cards resolve to reviewed vi/en/zh copy", () => {
  for (const locale of ["vi", "en", "zh"]) {
    for (const [key, route] of contentRoutes) {
      const html = renderModuleCard(locale, route, true, key);
      const titleKey = key === "feature_catalog"
        ? "featureCatalog.page.title"
        : key === "workspace_menu"
          ? "page.workspaceMenu.title"
          : `featureCatalog.entry.${key}.title`;
      const descriptionKey = key === "feature_catalog"
        ? "featureCatalog.page.description"
        : key === "workspace_menu"
          ? "page.workspaceMenu.description"
          : `featureCatalog.entry.${key}.description`;
      const title = i18n.t(titleKey);
      const description = i18n.t(descriptionKey);
      assert.ok(title && description, `${locale}.${key} copy must exist`);
      assert.ok(html.includes(title), `${locale}.${key} card must use its localized title`);
      assert.ok(html.includes(description), `${locale}.${key} card must use its localized description`);
      assert.ok(!html.includes("Registry title that must not override route copy"));
      assert.ok(!html.includes("Registry description that must not override route copy"));
    }
  }
});

test("content locale map covers every current registry key and route", () => {
  const registeredRoutes = [...registrySource.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*,\s*"content"\s*,\s*"([^"]+)"/g)]
    .map((match) => `${match[1]}\t${match[2]}`)
    .sort();
  assert.deepEqual(contentRoutes.map(([key, route]) => `${key}\t${route}`).sort(), registeredRoutes);
  assert.equal(contentRoutes.length, 30);
  assert.equal(new Set(contentRoutes.map(([key]) => key)).size, 30);
});
