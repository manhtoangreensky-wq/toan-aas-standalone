import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const portal = readFileSync("static/portal/portal.js", "utf8");
const css = readFileSync("static/portal/portal.css", "utf8");
const integration = readFileSync("static/portal/integration.js", "utf8");

const operationRoutes = [
  "/documents/split",
  "/documents/merge",
  "/documents/compress",
  "/documents/pdf-to-images",
  "/documents/image-to-pdf",
  "/documents/pdf-to-word",
  "/documents/ocr",
  "/documents/pdf-ocr",
  "/documents/pdf-ocr-to-word"
];

function functionSource(name) {
  const start = portal.indexOf(`  function ${name}(`);
  assert.notEqual(start, -1, `${name} exists`);
  const end = portal.indexOf("\n  }", start) + 4;
  assert.ok(end > start, `${name} has a bounded function body`);
  return portal.slice(start, end);
}

test("Documents keeps one canonical board and explicit operation routes", () => {
  assert.ok(portal.includes('customerPage("/documents", "Document Studio"'));
  assert.ok(portal.includes('layout: "document-hub", type: "document-hub"'));
  assert.ok(portal.includes('case "document-hub": return renderDocumentHub(page, context);'));
  for (const route of operationRoutes) assert.match(portal, new RegExp(`customerPage\\("${route.replaceAll("/", "\\/")}`));
  assert.doesNotMatch(portal, /customerPage\("\/document-hub"/);
});

test("Documents forms preserve source order, ranges, and guarded choices", () => {
  const split = functionSource("pdfSplitFormFields");
  const merge = functionSource("pdfMergeFormFields");
  const optimize = functionSource("pdfOptimizeFormFields");
  const imageToPdf = functionSource("imageToPdfFormFields");
  const pdfToImages = functionSource("pdfToImagesFormFields");
  const pdfToWord = functionSource("pdfToWordFormFields");
  const imageOcr = functionSource("imageOcrFormFields");
  const pdfOcr = functionSource("pdfOcrFormFields");
  const pdfOcrWord = functionSource("pdfOcrWordFormFields");

  assert.match(split, /name: "source_asset_id"/);
  assert.match(split, /name: "page_range"/);
  assert.match(split, /pattern: "\\\\d\+\(\?:-\\\\d\+\)\?"/);
  assert.match(merge, /Array\.from\(\{ length: 8 \}/);
  assert.match(merge, /name: `source_asset_id_\$\{position\}`/);
  assert.match(merge, /required = position <= 2/);
  assert.match(imageToPdf, /Array\.from\(\{ length: 8 \}/);
  assert.match(imageToPdf, /name: `source_asset_id_\$\{position\}`/);
  assert.match(optimize, /source_asset_id/);
  assert.match(optimize, /lossless/);
  for (const source of [pdfToImages, pdfToWord, imageOcr, pdfOcr, pdfOcrWord]) {
    assert.match(source, /source_asset_id/);
    assert.match(source, /language|2×|text/);
  }
  for (const source of [split, merge, imageToPdf, pdfToImages, pdfToWord, imageOcr, pdfOcr, pdfOcrWord]) {
    assert.match(source, /optionsFrom: "(?:pdfVaultAssets|imageVaultAssets)"/);
    assert.match(source, /Asset Vault|private|asset|server/);
  }
});

test("Documents presents vertical workflow groups and truthful preview/confirm/result states", () => {
  const start = portal.indexOf("  function renderDocumentHub(page, context)");
  const end = portal.indexOf("\n  function renderPdfSplit(page, context)", start);
  const board = portal.slice(start, end);
  for (const label of ["PDF cơ bản", "Chuyển đổi", "OCR & scan", "Chọn workflow", "Hoạt động gần đây"]) {
    assert.match(board, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  for (const route of operationRoutes) assert.match(board, new RegExp(`href: "${route.replaceAll("/", "\\/")}"`));
  assert.match(board, /data-document-tool-state="\$\{state\}"/);
  assert.match(board, /state === "ready" \? "Mở workflow" : "Xem điều kiện"/);
  assert.match(portal, /data-portal-confirm="Tách PDF/);
  assert.match(portal, /renderDocumentOperationCards\(operations/);
  assert.match(portal, /documentOperationDownloadPath\(item\)/);
  assert.match(portal, /documentOperationState\(item\) === "completed" && item && item\.download_ready === true/);
});

test("Documents keeps owner-scoped hydration and responsive vertical layout", () => {
  for (const token of [
    '"document-operation-view": Boolean(account && assetVaultEnabled && documentOperationsEnabled)',
    "async function hydrateDocumentOperations(offsetValue)",
    'api(documentOperationHistoryPath(kind, offset))',
    'api("/document-operations/pdf-split"',
    'api("/document-operations/pdf-merge"',
    'idempotency_key: submission.key'
  ]) assert.match(integration, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  for (const selector of [
    ".portal-document-operation-layout",
    ".portal-document-operation-form",
    ".portal-document-operation-grid",
    ".portal-document-board-workflow-groups",
    "@media (max-width: 760px)"
  ]) assert.match(css, new RegExp(selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.doesNotMatch(integration, /bridge_request/);
});
