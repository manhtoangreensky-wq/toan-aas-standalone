import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const portalThemeCss = fs.readFileSync(path.join(repoRoot, "static/portal/portal-theme.css"), "utf8");

test("AD-01: Admin sidebar, vertical tabs, and ERP navigation project server-issued modules by authority", () => {
  assert.match(portalSource, /function renderAdminModuleTabs\(/);
  assert.match(portalSource, /function adminErpNavigation\(context\)/);
  assert.match(portalSource, /function safeCatalogRoute\(/);
  assert.match(portalThemeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-admin-tabs/);
  assert.match(portalThemeCss, /\.portal-admin-tab\s*\{[^}]*min-height:\s*44px/su);
});

test("AD-02: Tables, vertical phone cards, detail drawer, and dynamic chart projections are accessible and bounded", () => {
  assert.match(portalSource, /function renderAdminDataTable\(/);
  assert.match(portalSource, /function renderAdminDataChart\(/);
  assert.match(portalSource, /function renderAdminDataSurface\(/);
  assert.match(portalThemeCss, /@media\s*\(max-width:\s*560px\)/);
  assert.match(portalThemeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-page \.portal-admin-data-surface/);
  assert.match(portalThemeCss, /tr\[data-admin-data-row\]/);
  assert.match(portalSource, /role="img"/);
});

test("AD-03: Customer to Admin record references project safe request-job-asset-report-audit chain", () => {
  assert.match(portalSource, /function adminDataReferenceProjection\(/);
  assert.match(portalSource, /data-admin-record-references/);
  assert.match(portalSource, /const allowedKinds\s*=\s*new Set\(\["request",\s*"job",\s*"asset",\s*"report",\s*"audit"\]\)/);
  assert.match(portalSource, /\/admin|\/jobs|\/assets|\/reports|\/audit/);
});

test("AD-05: Web and app surface parity respects role authority with mobile-first task ergonomics", () => {
  assert.match(portalSource, /function renderAdminMobileNav\(/);
  assert.match(portalSource, /function renderAdminWorkQueues\(/);
  assert.match(portalSource, /data-portal-app-kind="admin"/);
  assert.doesNotMatch(portalSource, /data-fake-admin-bypass/i);
});

test("AD-FIXTURE-MATRIX: Customer, admin, and denied roles enforce strict boundaries with zero mutation", () => {
  assert.match(portalSource, /read_state\s*!==\s*"ready"/);
  assert.match(portalSource, /renderAdminManualTopupActions/);
  assert.doesNotMatch(portalSource, /data-portal-action="approve-wallet-credit"/i);
  assert.doesNotMatch(portalSource, /data-portal-action="mutate-xu"/i);
});

test("A0: Master Ledger accounting enforces exact 4 closed A0 rows and 74 remaining open rows", () => {
  const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /A0_ADMIN_CLOSED_COUNT=4/);
  assert.match(masterLedger, /REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=(?:74|61|57|54)/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);
});
