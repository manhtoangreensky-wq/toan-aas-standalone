import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");

const catalogueStart = i18nSource.indexOf("  const IMAGE_OPERATION_COPY_ROWS = [");
const catalogueEnd = i18nSource.indexOf("\n  ];", catalogueStart);
assert.ok(catalogueStart >= 0 && catalogueEnd > catalogueStart, "Image operation catalogue boundary must remain present");
const catalogue = i18nSource.slice(catalogueStart, catalogueEnd);
const rows = [...catalogue.matchAll(/^\s*\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\],\r?$/gm)];
const vi = rows.map((match) => match[2]);
const en = rows.map((match) => match[3]);
const zh = rows.map((match) => match[4]);
const keys = new Set(rows.map((match) => match[1]));

function functionBody(name, nextName) {
  const start = portalSource.indexOf(`  function ${name}(`);
  const end = portalSource.indexOf(`  function ${nextName}(`, start);
  assert.ok(start >= 0 && end > start, `${name} renderer boundary must remain present`);
  return portalSource.slice(start, end);
}

const storyboardRenderer = functionBody("renderStoryboardGrid", "renderImageResize");
const historyRenderer = functionBody("renderImageOperationHistory", "renderImageBrandOverlay");
const historyCardsRenderer = functionBody("renderImageHistoryOperationCards", "renderDocumentOperationCards");
const exportRenderer = functionBody("imageOperationAssetExportControl", "storyboardGridDownloadPath");

const requiredKeys = [
  "common.guard.ownerScoped",
  "brand.guard.publicPreview",
  "storyboard.guard.title",
  "storyboard.guard.body",
  "storyboard.loading.body",
  "storyboard.failed.body",
  "storyboard.runReason.capability",
  "storyboard.runReason.disabled",
  "storyboard.runReason.empty",
  "storyboard.runReason.ready",
  "storyboard.form.title",
  "storyboard.form.description",
  "storyboard.form.confirm",
  "storyboard.form.submit",
  "storyboard.boundary.title",
  "storyboard.boundary.description",
  "storyboard.results.title",
  "storyboard.results.description",
  "storyboard.notice.title",
  "storyboard.notice.body",
  "history.guard.title",
  "history.guard.body",
  "history.loading.title",
  "history.loading.body",
  "history.failed.title",
  "history.failed.body",
  "history.intro.title",
  "history.intro.body",
  "history.results.title",
  "history.results.description",
  "history.boundary.title",
  "history.boundary.body",
  "common.exportConfirm",
  "common.handoffConfirm",
  "common.continueConfirm"
];

const genericEnglish = /\b(?:review|server|provider|browser|source|output|private|signed|account|owner|scoped|history|download|preview|cache|fallback|deterministic|utility|splitter|cell|cells|grid|settings|type|frame|profile|overlay|status|state|integrity|ownership|delivery|archive|public|loading|failed|retry|current|workspace|operation|operations)\b/i;

test("Image operation catalogue is balanced and complete for vi/en/zh", () => {
  assert.ok(rows.length >= 300, "Image operation catalogue must retain the complete reviewed key set");
  assert.equal(keys.size, rows.length, "Image operation locale keys must be unique");
  assert.equal(vi.length, en.length);
  assert.equal(vi.length, zh.length);
  for (const key of requiredKeys) assert.ok(keys.has(key), `Missing image operation locale key: ${key}`);
  assert.doesNotMatch(vi.join(" | ").replace(/\{[^}]+\}/g, ""), genericEnglish, "Vietnamese fixed copy must not leak generic English UI jargon");
  assert.doesNotMatch(en.join(" | "), /[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i, "English catalogue must not contain Vietnamese diacritics");
  assert.doesNotMatch(zh.join(" | "), /Công cụ|Tạo|Chọn|Đang|Không|Thư viện/, "Chinese catalogue must not contain Vietnamese copy");
});

test("Image operation renderers use locale helpers and keep the fixed contracts", () => {
  for (const helper of ["imageOperationText", "renderStoryboardGrid", "renderImageOperationHistory", "renderImageHistoryOperationCards", "imageOperationAssetExportControl"]) {
    assert.match(portalSource, new RegExp(`function ${helper}\\(`));
  }
  for (const stale of [
    "Storyboard Grid Splitter đang ở chế độ an toàn",
    "signed Web session",
    "storage private riêng",
    "source reference",
    "server-side",
    "Brand Overlay Studio không tạo Bot job",
    "Tiện ích Web-native độc lập",
    "Private Image History",
    "không trộn authority",
    "PNG output",
    "Owner-scoped",
    "Image Enhance",
    "Resize & Aspect"
  ]) {
    assert.doesNotMatch(`${storyboardRenderer}\n${historyRenderer}\n${historyCardsRenderer}\n${exportRenderer}`, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `Stale fixed copy remains: ${stale}`);
  }
  for (const contract of [
    'data-portal-action="image-operation-resize"',
    'data-portal-action="image-operation-enhance"',
    'data-portal-action="image-brand-overlay"',
    'data-portal-action="storyboard-grid-create"'
  ]) {
    assert.match(portalSource, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `Contract changed: ${contract}`);
  }
  for (const field of [
    "source_asset_id", "preset", "target_width", "target_height", "fit_mode", "brightness", "contrast",
    "saturation", "sharpness", "tone", "basic_upscale", "logo_asset_id", "overlay_text", "text_position",
    "logo_position", "logo_scale_percent", "logo_opacity_percent", "episode", "rows", "cols", "start_scene", "trim_percent"
  ]) {
    assert.match(portalSource, new RegExp(`(?:name\\s*:\\s*[\"']${field}[\"']|name=[\"']${field}[\"'])`), `Contract changed: ${field}`);
  }
});

test("Image operation downloads stay fail-closed", () => {
  assert.match(portalSource, /imageOperationState\(item\) === "completed"[\s\S]*?item\.download_ready === true/);
  assert.match(portalSource, /storyboardGridCellDownloadPath[\s\S]*?imageOperationState\(operation\) === "completed"[\s\S]*?cell\.download_ready === true/);
  assert.match(portalSource, /function imageOperationAssetExportControl[\s\S]*?imageOperationState\(item\) === "completed"[\s\S]*?item\.download_ready === true/);
});
