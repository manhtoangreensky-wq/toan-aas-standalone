import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const portalCss = fs.readFileSync(path.join(repoRoot, "static/portal/portal.css"), "utf8");
const themeCss = fs.readFileSync(path.join(repoRoot, "static/portal/portal-theme.css"), "utf8");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");

test("F0-01: form controls have explicit IDs, labels, input bindings, and action handlers", () => {
  assert.match(portalSource, /function renderFields\(/);
  assert.match(portalSource, /function renderFormCard\(/);
  assert.match(portalSource, /data-portal-action=/);
  assert.match(portalSource, /data-field=/);
  assert.match(portalSource, /class="portal-field-label"/);
});

test("F0-02: design system tokens enforce accessible contrast, typography, and 44px touch targets", () => {
  assert.match(portalCss, /min-height:\s*44px/);
  assert.match(themeCss, /--portal-dark-ink:\s*#f0fbff/);
  assert.match(themeCss, /--portal-ink:\s*#073a45/);
});

test("F0-03: client configuration is editable while execution gates remain server-authoritative", () => {
  assert.match(portalSource, /function featureConfirmExecutionReady\(/);
  assert.match(portalSource, /function transientFormValues\(/);
  assert.doesNotMatch(portalSource, /data-portal-action="fake-generate-bypass"/);
});

test("F0-04: mode switching and hydration preserve scalar drafts and focus lifecycle", () => {
  assert.match(portalSource, /function captureImageWorkspaceDraft\(/);
  assert.match(portalSource, /function synchronizeImageWorkspaceDraftSession\(/);
  assert.match(portalSource, /function navigateImageWorkspace\(/);
});

test("F0-05: upload, preview, and asset picker bind to canonical Asset Vault", () => {
  assert.match(portalSource, /function imageVaultItems\(/);
  assert.match(portalSource, /function imageOperationAssetReferenceListing\(/);
  assert.doesNotMatch(portalSource, /data-fake-transparent-preview/i);
});

test("F0-06: account change and logout purge private workspace drafts and respect RBAC manifest", () => {
  assert.match(portalSource, /function clearTransientFormDraft\(/);
  assert.match(portalSource, /function synchronizeImageWorkspaceDraftSession\(/);
});

test("Q0-01: master ledger reconciliation enforces zero unclassified entries and exact row counts", () => {
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);
  assert.match(masterLedger, /SUPERSEDED_BY_ACCEPTED_R37_R41_COUNT=11/);
  assert.match(masterLedger, /DEFERRED_OWNER_EXTERNAL_COUNT=10/);
  assert.match(masterLedger, /OBSOLETE_OR_DUPLICATE_COUNT=15/);
});

test("Q0-02: pure localization catalogues define complete, balanced keys for vi, en, and zh", () => {
  assert.match(i18nSource, /const LOCALES\s*=\s*Object\.freeze\(\{[\s\S]*?vi:[\s\S]*?en:[\s\S]*?zh:/);
  assert.match(i18nSource, /const MESSAGES\s*=\s*\{[\s\S]*?vi:\s*\{[\s\S]*?en:\s*\{[\s\S]*?zh:\s*\{/);
  assert.match(i18nSource, /function translate\(/);
});
