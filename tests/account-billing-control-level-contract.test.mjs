import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const integration = fs.readFileSync("static/portal/integration.js", "utf8");

function between(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle);
  const end = source.indexOf(endNeedle, start + startNeedle.length);
  assert.ok(start >= 0 && end > start, `missing source boundary: ${startNeedle}`);
  return source.slice(start, end);
}

const wallet = between(portal, "  function renderWallet(page, context)", "  const DEFAULT_CANONICAL_PACKAGES");
const paymentGate = between(portal, "  function paymentWebCatalogReady(context)", "  function renderBillingWorkspaceNav");
const manual = between(portal, "  function renderManualTopupGuide(context)", "  function renderPaymentRequestForm");
const payos = between(portal, "  function renderPaymentRequestForm(page, context)", "  function renderPaymentLookup");
const catalog = between(portal, "  function renderCatalog(page, context)", "  function jobStatus(");
const adminTopup = between(portal, "  function renderAdminManualTopupActions(record, writeEnabled)", "  function renderAdminPricingCard");

test("AC-02A wallet and history stay canonical, bounded and refreshable", () => {
  for (const marker of [
    "walletReadState(context)",
    "canonicalWalletProjection(context.wallet)",
    "canonicalWalletHistoryProjection(context.walletHistory)",
    'data-portal-action="wallet-refresh"',
    "walletReady = readState === \"ready\""
  ]) assert.ok(wallet.includes(marker), `missing wallet marker: ${marker}`);
  assert.doesNotMatch(wallet, /balance_xu\s*\|\|\s*0/);
  assert.doesNotMatch(wallet, /walletHistory\.map\(/);
});

test("AC-02B manual top-up requires method plus amount before private QR and pending request", () => {
  for (const marker of [
    "manualTopupMethodHasCanonicalQr",
    "manual_selection_confirmed",
    "confirmed_amount_vnd",
    "confirmed_method",
    'data-portal-action="manual-topup-confirm-selection"',
    'data-portal-action="manual-topup-create"',
    "Web không tự cộng Xu",
    "slice(0, 50)"
  ]) assert.ok(manual.includes(marker), `missing manual top-up marker: ${marker}`);
  const beforeConfirmation = between(manual, "if (!isSelectionConfirmed)", "const item = confirmedMethodDest");
  assert.doesNotMatch(beforeConfirmation, /<img\b/);
  const afterConfirmation = manual.slice(manual.indexOf("const item = confirmedMethodDest"));
  assert.match(afterConfirmation, /safeQrUrl/);
  assert.ok(afterConfirmation.includes("/api/v1/payments/options/manual-methods/"));
});

test("AC-02B/AC-02C payment and catalog lanes fail closed without server capability", () => {
  assert.match(paymentGate, /request_enabled === true/);
  assert.match(paymentGate, /topup_catalog_available === true/);
  assert.match(paymentGate, /\["payment-create"\] === true/);
  assert.match(payos, /data-portal-action="payment-create"/);
  assert.match(payos, /disabled aria-disabled/);
  assert.match(payos, /topup_packages/);
  assert.doesNotMatch(payos, /PAYMENT_DISPLAY_FALLBACK_PACKAGES/);
  assert.match(portal, /protocol === "https:"/);
  assert.match(portal, /pay\.payos\.vn/);
});

test("AC-02C PayOS never renders browser-owned packages when server catalog is empty", () => {
  assert.doesNotMatch(portal, /const PAYMENT_DISPLAY_FALLBACK_PACKAGES/);
  assert.doesNotMatch(payos, /serverPackages\.length \? serverPackages :/);
  assert.match(payos, /const packages = serverPackages\.flatMap/);
  assert.match(payos, /topup_packages/);
  assert.match(payos, /Cổng PayOS hoặc danh mục mệnh giá hiện chưa sẵn sàng/);
});

test("AC-02C packages and pricing are read-only canonical catalogs", () => {
  for (const marker of ["canonicalPricingCatalog", "canonicalPackageCatalog", "catalogReady", "read_only", "/wallet/topup"]) {
    assert.ok(catalog.includes(marker), `missing catalog marker: ${marker}`);
  }
  assert.doesNotMatch(catalog, /<form\b/);
  assert.doesNotMatch(catalog, /data-portal-action=/);
  assert.doesNotMatch(catalog, /payment-create/);
});

test("AC-02D Admin handoff keeps request identity, status, revision and final confirmation boundary", () => {
  for (const marker of [
    "pending_admin_review",
    "request_id",
    "expected_xu",
    "writeEnabled",
    'data-portal-action="admin-manual-topup-draft"',
    "confirmation_receipt",
    'data-portal-action="admin-manual-topup-confirm"',
    "admin-manual-topup-cancel-confirmation"
  ]) assert.ok(adminTopup.includes(marker), `missing admin top-up marker: ${marker}`);
  assert.match(integration, /["']admin-manual-topup-view["']/);
  assert.match(integration, /["']admin-manual-topup-write["']/);
  assert.match(adminTopup, /pending_admin_review/);
  assert.match(adminTopup, /rejected/);
});
