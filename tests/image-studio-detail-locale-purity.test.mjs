import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");

const catalogueStart = i18nSource.indexOf("  const IMAGE_STUDIO_DETAIL_COPY_ROWS = [");
const catalogueEnd = i18nSource.indexOf("\n  ];", catalogueStart);
assert.ok(catalogueStart >= 0 && catalogueEnd > catalogueStart, "Image Studio detail catalogue boundary must remain present");
const catalogue = i18nSource.slice(catalogueStart, catalogueEnd);
const rows = [...catalogue.matchAll(/^\s*\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\],$/gm)];
const vi = rows.map((match) => match[2]);
const en = rows.map((match) => match[3]);
const zh = rows.map((match) => match[4]);
const detailStart = portalSource.indexOf("  function imageStudioEstimateMarkup(");
const detailEnd = portalSource.indexOf("  // AI Chat Workspace", detailStart);
assert.ok(detailStart >= 0 && detailEnd > detailStart, "Image Studio detail renderer boundary must remain present");
const renderer = portalSource.slice(detailStart, detailEnd);

const genericEnglish = /\b(?:review|estimate|server|provider|browser|workspace|image|creative|direction|self-review|artboard|metadata|reference|archive|restore|version|history|prompt|visual|private|deterministic|output|thumbnail|preview|raw|blob|feed|activity|current|open|save|draft|guarded|studio|operations|active|status|variant|notes|library)\b/i;

test("Image Studio detail catalogue stays balanced and Vietnamese fixed copy is clean", () => {
  assert.equal(rows.length, 91, "Image Studio detail catalogue must keep every reviewed key");
  assert.equal(new Set(rows.map((match) => match[1])).size, rows.length, "Detail locale keys must be unique");
  assert.equal(vi.length, en.length);
  assert.equal(vi.length, zh.length);
  assert.doesNotMatch(vi.join(" | ").replace(/\{[^}]+\}/g, ""), genericEnglish);
  assert.doesNotMatch(en.join(" | "), /[À-ỹ]/);
  assert.doesNotMatch(zh.join(" | "), /Công cụ|Tạo|Chọn|Đang|Không|Thư viện/);
});

test("Image Studio detail chrome uses the locale helper without changing action contracts", () => {
  assert.match(portalSource, /function imageStudioDetailText\(/);
  assert.match(portalSource, /function imageStudioEventLabel\(/);
  for (const stale of [
    "Review estimate",
    "Tổng hợp metadata để rà soát",
    "directions active",
    "Asset Vault refs",
    "variant metadata",
    "Archive biến thể direction",
    "Archive artboard",
    "Review-safe local utilities",
    "Variant direction board",
    "Direction library",
    "Version history",
    "Audit-safe feed",
    "signed session",
    "server-side",
    "optimistic revision",
    "Có ảnh private cần xử lý deterministic?"
  ]) assert.doesNotMatch(renderer, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
  for (const helper of [
    "imageStudioDetailText",
    "imageStudioEstimateMarkup",
    "renderImageDirectionCard",
    "renderImageStudioDetail",
    "imageStudioEventLabel"
  ]) assert.match(portalSource, new RegExp(`function ${helper}\\(`));
  for (const contract of [
    'data-portal-action="image-artboard-state"',
    'data-portal-action="image-artboard-update"',
    'data-portal-action="image-artboard-restore-version"',
    'data-portal-action="image-direction-create"',
    'data-portal-action="image-direction-update"',
    'data-portal-action="image-direction-archive"',
    'data-portal-action="image-direction-restore"',
    'data-image-artboard-revision="${safeText(String(artboard.revision))}"',
    'data-image-direction-revision="${safeText(String(direction.revision))}"'
  ]) assert.match(renderer, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
});
