import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");

const catalogueStart = i18nSource.indexOf("  const IMAGE_STUDIO_LIBRARY_COPY_ROWS = [");
const catalogueEnd = i18nSource.indexOf("\n  ];", catalogueStart);
assert.ok(catalogueStart >= 0 && catalogueEnd > catalogueStart, "Image Studio library catalogue boundary must remain present");
const catalogue = i18nSource.slice(catalogueStart, catalogueEnd);
const rows = [...catalogue.matchAll(/^\s*\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\],$/gm)];
const vi = rows.map((match) => match[2]);
const en = rows.map((match) => match[3]);
const zh = rows.map((match) => match[4]);
const rendererStart = portalSource.indexOf("  function renderImageStudioArtboardPagination(");
const rendererEnd = portalSource.indexOf("  function renderImageStudio(page, context)", rendererStart);
assert.ok(rendererStart >= 0 && rendererEnd > rendererStart, "Image Studio library renderer boundary must remain present");
const renderer = portalSource.slice(rendererStart, rendererEnd);

const genericEnglish = /\b(?:server|provider|workspace|image|creative|direction|self-review|artboard|metadata|target|brief|style|job|delivery|wallet|payment|review|reference|library|operations|active|status|refresh|find|open|account|current|read-only|prompt)\b/i;

test("Image Studio library catalogue stays balanced and Vietnamese fixed copy is clean", () => {
  assert.equal(rows.length, 67, "Image Studio library catalogue must keep every reviewed key");
  assert.equal(new Set(rows.map((match) => match[1])).size, rows.length, "Library locale keys must be unique");
  assert.equal(vi.length, en.length);
  assert.equal(vi.length, zh.length);
  assert.doesNotMatch(vi.join(" | ").replace(/\{[^}]+\}/g, ""), genericEnglish);
  assert.doesNotMatch(en.join(" | "), /[À-ỹ]/);
  assert.doesNotMatch(zh.join(" | "), /Công cụ|Tạo|Chọn|Đang|Không|Thư viện/);
});

test("Image Studio libraries and Hub use the reviewed locale helper without changing route/action contracts", () => {
  for (const stale of [
    "Reference library",
    "Project context",
    "Asset Vault context",
    "Tìm reference",
    "Artboard library",
    "Tiếp tục creative review",
    "signed account",
    "owner-check",
    "Image operations board",
    "Independent next steps",
    "Direction review board"
  ]) assert.doesNotMatch(renderer, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
  for (const helper of ["imageStudioLibraryText", "renderImageStudioReferencePicker", "renderImageStudioReferenceLibrary", "renderImageStudioArtboardLibrary", "renderImageArtboardCards", "renderImageHubOverview", "renderImageHubNextSteps", "renderImageHubDetailBoard"]) {
    assert.match(portalSource, new RegExp(`function ${helper}\\(`));
  }
  for (const contract of [
    'data-portal-action="image-studio-refresh"',
    'data-portal-action="image-studio-filter"',
    'const actionPrefix = projects ? "image-studio-project-reference" : "image-studio-asset-reference"',
    'actionPrefix + "-filter"',
    'data-image-studio-offset',
    'data-image-studio-project-reference-offset',
    'data-image-studio-asset-reference-offset'
  ]) assert.match(portalSource, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
});
