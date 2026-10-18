import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const portal = readFileSync("static/portal/portal.js", "utf8");
const integration = readFileSync("static/portal/integration.js", "utf8");
const css = readFileSync("static/portal/portal.css", "utf8");

function functionSource(source, name) {
  const start = [
    source.indexOf(`  function ${name}(`),
    source.indexOf(`  async function ${name}(`)
  ].filter((index) => index >= 0).sort((a, b) => a - b)[0] ?? -1;
  assert.notEqual(start, -1, `${name} exists`);
  const end = source.indexOf("\n  }", start) + 4;
  assert.ok(end > start, `${name} has a bounded function body`);
  return source.slice(start, end);
}

test("Asset Vault keeps one owner-scoped vertical workspace with truthful states", () => {
  const render = functionSource(portal, "renderAssetVault");
  for (const token of [
    'const listing = assetVaultListing(context);',
    'const items = assetVaultLibraryItems(context);',
    'data-portal-action="asset-vault-upload"',
    'data-portal-action="asset-vault-filter"',
    'data-portal-action="asset-vault-refresh"',
    'data-portal-action="asset-vault-lifecycle-open"',
    'data-portal-action="asset-vault-archive"',
    'vaultDownloadPath(item)',
    'itemState === "active"',
    'Tệp đã lưu trữ; tải về đang khóa.',
    'Không có fallback sang static, browser storage hoặc Tài sản Bot.'
  ]) assert.match(render, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.match(render, /accept="\.jpg,\.jpeg,\.png,\.webp,\.mp4,\.mov,\.webm,\.mp3,\.wav,\.m4a,\.ogg,\.pdf,\.txt,\.srt,\.vtt,\.docx"/);
  assert.match(render, /tối đa 25 MB/);
});

test("Asset Vault exposes explicit filter, pagination, lifecycle and project-link controls", () => {
  const filter = functionSource(portal, "assetVaultFilterFields");
  const pagination = functionSource(portal, "renderAssetVaultPagination");
  const lifecycle = functionSource(portal, "assetVaultLifecyclePanel");
  const form = functionSource(portal, "assetVaultFormFields");
  for (const state of ["active", "archived", "all"]) assert.match(filter, new RegExp(state));
  for (const token of [
    'data-portal-action="asset-vault-page"',
    'data-asset-vault-offset',
    'data-portal-action="asset-vault-lifecycle-close"',
    'data-portal-action="asset-vault-lifecycle-restore"',
    'restore_available',
    'data-portal-confirm="Khôi phục tệp này vào Asset Vault đang hoạt động?',
    'name: "project_id"',
    'optionsFrom: "projects"'
  ]) {
    const source = [pagination, lifecycle, form].join("\n");
    assert.match(source, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(lifecycle, /reference_summary/);
  assert.match(lifecycle, /Không hiển thị path, hash, storage key, case hay operation ID/);
});

test("Asset Vault hydration is owner-scoped, paginated and fail-closed", () => {
  const listPath = functionSource(integration, "assetVaultListPath");
  const listProjection = functionSource(integration, "assetVaultListingProjection");
  const listFence = functionSource(integration, "assetVaultRequestIsCurrent");
  const lifecycleFence = functionSource(integration, "assetVaultLifecycleRequestIsCurrent");
  for (const token of [
    "ASSET_VAULT_LIST_LIMIT",
    "offset",
    "state",
    "next_offset",
    "previous_offset",
    "assetVaultSessionEpoch",
    "currentPortalPath() === expectedPath",
    "base().assetVaultEnabled === true",
    "base().session && base().session.authenticated === true",
    "assetVaultLifecycleSelectionId() === assetId"
  ]) {
    const source = [listPath, listProjection, listFence, lifecycleFence].join("\n");
    assert.match(source, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  const hydration = functionSource(integration, "hydrateAssetVault");
  assert.match(hydration, /api\(assetVaultListPath\(filter, offset\)\)/);
  assert.match(hydration, /vaultItems: \[\]/);
  assert.match(hydration, /assetVaultReadState: "failed"/);
  assert.match(hydration, /never falls back to Bot assets or browser storage/i);
});

test("Asset Vault mutations require a real file, CSRF capability, idempotency and server lifecycle revision", () => {
  const actionStart = integration.indexOf('      if (action === "asset-vault-upload")');
  const actionEnd = integration.indexOf('      if (["document-asset-reference-filter"', actionStart);
  assert.ok(actionStart >= 0 && actionEnd > actionStart, "Asset Vault action block is bounded");
  const actions = integration.slice(actionStart, actionEnd);
  for (const token of [
    'if (action === "asset-vault-upload")',
    'new FormData()',
    'headers: { "Idempotency-Key": submission.key }',
    'expected_revision: expectedRevision',
    'api(`/asset-vault/${encodeURIComponent(assetId)}/archive`',
    'api(`/asset-vault/${encodeURIComponent(assetId)}/restore`',
    'hydrateAssetVaultLifecycle(assetId)',
    'discardSubmission(`asset-vault:${assetId}:archive`, submission)',
    'discardSubmission(`asset-vault:${assetId}:restore`, submission)'
  ]) assert.match(actions, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  for (const token of [
    '"asset-vault-upload": Boolean(account && me.csrf_token && assetVaultEnabled)',
    '"asset-vault-archive": Boolean(account && me.csrf_token && assetVaultEnabled)',
    '"asset-vault-restore": Boolean(account && me.csrf_token && assetVaultEnabled)'
  ]) assert.match(integration, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.doesNotMatch(actions, /bridge_request|provider|wallet|PayOS/);
});

test("Asset Vault keeps the existing blue/teal surface and collapses to one readable column", () => {
  for (const selector of [
    ".portal-asset-vault",
    ".portal-vault-layout",
    ".portal-vault-grid",
    ".portal-vault-dropzone",
    ".portal-vault-pagination",
    "@media (max-width: 760px)"
  ]) assert.match(css, new RegExp(selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.match(css, /\.portal-vault-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2/);
  assert.match(css, /\.portal-vault-grid\s*\{[^}]*grid-template-columns:\s*1fr/);
  assert.doesNotMatch(css, /\.portal-page\.portal-asset-vault[^}]*background:\s*(?:#000|black)/i);
});
