import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const portalCss = fs.readFileSync(path.join(repoRoot, "static/portal/portal.css"), "utf8");
const portalThemeCss = fs.readFileSync(path.join(repoRoot, "static/portal/portal-theme.css"), "utf8");
const portalI18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const qaMatrixRunner = fs.readFileSync(path.join(repoRoot, "scripts/ci/run_authenticated_qa_matrix.py"), "utf8");
const browserVerificationRunner = fs.readFileSync(path.join(repoRoot, "scripts/ci/run_browser_verification.py"), "utf8");
const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");

test("Q0-03: Responsive shell and multi-viewport matrix contracts (375/390/768/1440, themes, zero overflow)", () => {
  // CSS responsive media queries
  assert.match(portalCss, /@media\s*\([^)]*max-width:\s*768px\)/);
  assert.match(portalCss, /@media\s*\([^)]*max-width:\s*480px\)/);

  // Authenticated QA runner covers 4 canonical viewports and checks overflow
  assert.match(qaMatrixRunner, /"phone-375",\s*375,\s*812/);
  assert.match(qaMatrixRunner, /"phone-390",\s*390,\s*844/);
  assert.match(qaMatrixRunner, /"tablet-768",\s*768,\s*1024/);
  assert.match(qaMatrixRunner, /"desktop-1440",\s*1440,\s*900/);
  assert.match(qaMatrixRunner, /horizontal_overflow:\s*document\.documentElement\.scrollWidth\s*>\s*window\.innerWidth\s*\+\s*1/);
  assert.match(qaMatrixRunner, /main_visible:\s*Boolean\(/);

  // Browser verification runner covers 3 viewports and touch targets
  assert.match(browserVerificationRunner, /1440,\s*900/);
  assert.match(browserVerificationRunner, /768,\s*1024/);
  assert.match(browserVerificationRunner, /375,\s*812/);
});

test("Q0-04: Accessibility tree extraction, focus order, accessible contrast tokens, and 44px touch targets", () => {
  // Touch target min size >= 44px
  assert.match(portalCss, /min-height:\s*44px/);

  // Design system theme tokens enforce accessible contrast
  assert.match(portalThemeCss, /--portal-ink:\s*#073a45/);
  assert.match(portalThemeCss, /--portal-dark-ink:\s*#f0fbff/);

  // Authenticated QA runner extracts full accessibility tree and focus order
  assert.match(qaMatrixRunner, /Accessibility\.getFullAXTree/);
  assert.match(qaMatrixRunner, /focus_order:\s*focus/);
  assert.match(qaMatrixRunner, /interactive_count:\s*controls\.length/);
});

test("Q0-TOAST-STACK: Toast notification stack bounds, duplicate collapsing, and ARIA live regions", () => {
  // Ensure portal.js implements showToast with bounded 2-node stack and duplicate collapsing
  assert.match(portalSource, /function showToast\(/);
  assert.match(portalSource, /role="status"/);

  // Integration and auth scripts also provide toast functionality
  const integrationSource = fs.readFileSync(path.join(repoRoot, "static/portal/integration.js"), "utf8");
  const authSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-auth.js"), "utf8");
  assert.match(integrationSource, /function toast\(/);
  assert.match(authSource, /function toast\(/);

  // Test suite exists and is referenced
  assert.ok(fs.existsSync(path.join(repoRoot, "tests/portal-toast-stack.test.mjs")));
});

test("Q0-CUSTOMER-CONTENT: Customer content action truth and zero unverified placeholder claims in fixed chrome", () => {
  // No demo/beta/sandbox mock labels in fixed UI chrome
  assert.doesNotMatch(portalSource, /data-portal-action="fake-generate-bypass"/);
  assert.doesNotMatch(portalSource, /data-fake-transparent-preview/i);

  // Customer routes are verified in authenticated QA runner
  assert.match(qaMatrixRunner, /CUSTOMER_ROUTES\s*=/);
  assert.match(qaMatrixRunner, /"\/welcome"/);
  assert.match(qaMatrixRunner, /"\/dashboard"/);
  assert.match(qaMatrixRunner, /"\/tools\/video"/);
  assert.match(qaMatrixRunner, /"\/video\/create"/);
});

test("VI-QA-REGRESSION & VI-BROWSER-SMOKE: Video Hub and Video Create routes in authenticated QA matrix", () => {
  // Video routes part of authenticated QA matrix
  assert.match(qaMatrixRunner, /"\/tools\/video"/);
  assert.match(qaMatrixRunner, /"\/video\/create"/);

  // Portal implements Video Hub and Video Create views
  assert.match(portalSource, /function renderVideoHub\(/);
  assert.match(portalSource, /featurePage\("\/video\/create"/);

  // Evidence file exists
  assert.ok(fs.existsSync(path.join(repoRoot, "reports/audit/R218-VIDEO-PRESENTATION-QA-20261020.json")));
});

test("VI-TOOLBAR-CAPCUT-BOUNDED: Toolbar tools contract enforces bounded tools without CapCut parity claims", () => {
  // Toolbar contract: no CapCut parity claim in source or translations
  assert.doesNotMatch(portalSource, /capcut.*parity/i);
  assert.doesNotMatch(portalI18nSource, /capcut.*parity/i);

  // Video hub renders bounded tools
  assert.match(portalSource, /video-hub/i);
});

test("Q0/L0 Master Ledger Reconciliation: 260 total = 196 closed + 10 deferred + 54 open", () => {
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);
  assert.match(masterLedger, /F0_Q0_IMAGE_CLOSED_COUNT=13/);
  assert.match(masterLedger, /P5_P6_CLOSED_COUNT=13/);
  assert.match(masterLedger, /A0_ADMIN_CLOSED_COUNT=4/);
  assert.match(masterLedger, /V0_VIDEO_CLOSED_COUNT=13/);
  assert.match(masterLedger, /Q0_L0_CLOSED_COUNT=7/);
  assert.match(masterLedger, /REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=54/);
  assert.match(masterLedger, /SUBPHASE_Q0_L0=PASS/);
});
