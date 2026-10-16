import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");

const catalogueStart = i18nSource.indexOf("  const IMAGE_STUDIO_COPY_ROWS = [");
const catalogueEnd = i18nSource.indexOf("\n  ];", catalogueStart);
assert.ok(catalogueStart >= 0 && catalogueEnd > catalogueStart, "Image Studio catalogue boundary must remain present");
const catalogue = i18nSource.slice(catalogueStart, catalogueEnd);
const rows = [...catalogue.matchAll(/^\s*\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\],$/gm)];
const vi = rows.map((match) => match[2]);
const en = rows.map((match) => match[3]);
const zh = rows.map((match) => match[4]);
const renderStart = portalSource.indexOf("  function renderImageStudio(page, context)");
const renderEnd = portalSource.indexOf("  function imageStudioEstimateMarkup", renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart, "Image Studio renderer boundary must remain present");
const renderer = portalSource.slice(renderStart, renderEnd);

const genericEnglish = /\b(?:signed|server|provider|browser|workspace|image|creative|direction|self-review|artboard|review|metadata|target|brief|style|asset|job|delivery|wallet|payment|archive|guarded|native|legacy|fallback|thumbnail|preview)\b/i;

test("Image Studio locale catalogue stays balanced and Vietnamese fixed copy is clean", () => {
  assert.equal(rows.length, 37, "Image Studio fixed catalogue must keep every reviewed key");
  assert.equal(vi.length, en.length);
  assert.equal(vi.length, zh.length);
  assert.doesNotMatch(vi.join(" | ").replace(/\{[^}]+\}/g, "").replace(/\/image\b/g, ""), genericEnglish);
});

test("Image Studio guard and creation chrome use the locale helper without changing contracts", () => {
  for (const stale of [
    "Image Creative Studio đang được server giữ ở chế độ guarded",
    "Image Operations Hub đang được bảo vệ",
    "Web-native visual direction",
    "New creative artboard",
    "Authoring boundary",
    "Provider image call",
    "Image / preview",
    "Job / delivery",
    "Wallet / payment"
  ]) assert.doesNotMatch(renderer, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
  for (const helper of ["imageStudioText", "imageStudioIntentOptions", "imageStudioFormatOptions", "imageStudioStateOptions"]) {
    assert.match(portalSource, new RegExp(`function ${helper}\\(`));
  }
  for (const contract of [
    'data-portal-action="image-artboard-create"',
    'data-portal-route="${safeText(page.routePath || page.path)}"',
    'name: "image_intent"',
    'name: "output_format"',
    'CSRF',
    'idempotency'
  ]) assert.match(portalSource, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
});
