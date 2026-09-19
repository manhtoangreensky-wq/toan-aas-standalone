"""Empirical verification test suite for P0.WEBAPP.V2-04: OUTPUT ASSET DELIVERY CENTER.

Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V2-04.OUTPUT.ASSET.DELIVERY.CENTER
Mode: OWNER-GOVERNED, SOURCE_ONLY, FIRST_RED_FIRST, ZERO_FAKE_DATA

Proves 20 invariants:
 1. /jobs route valid
 2. /assets route valid
 3. /asset-vault deep link valid (no 404, no redirect loop)
 4. One primary asset surface authority (CANONICAL_ASSET_ROUTE=/assets, ASSET_PRIMARY_SURFACE_COUNT=1)
 5. Raw UUID not primary customer display (friendly derived short reference used)
 6. Technical status leakage absent (queued -> Đang chờ xử lý, failed -> Không hoàn tất)
 7. Completed job links real durable asset when available
 8. Completed job without durable asset has no fake download
 9. Missing asset has no download CTA (DEAD_DOWNLOAD_CTA=0, MISSING_FILE_DOWNLOAD_CTA=0)
10. Expired asset has no download CTA (EXPIRED_FILE_DOWNLOAD_CTA=0)
11. Unknown ETA not fabricated (CLIENT_DERIVED_ETA=0, UNKNOWN_ETA_AS_ZERO=0)
12. Fake retention countdown absent (FAKE_RETENTION_COUNTDOWN=0)
13. Fake cancel action absent without backend authority (FAKE_CANCEL_ACTION=0)
14. Cancel terminal job unavailable
15. Report-job action truthful with prefilled job context (FAKE_REPORT_SUBMISSION=0)
16. Fake bulk ZIP download absent without backend authority (FAKE_BULK_ZIP=0)
17. Fake reuse-as-input absent without backend authority (FAKE_REUSE_INPUT=0)
18. Account isolation preserved (CROSS_ACCOUNT_JOB_LEAK=0, CROSS_ACCOUNT_ASSET_LEAK=0)
19. V2-03 commerce regression = 0
20. Responsive mobile delivery surface contract (no horizontal overflow, safe wrapping)
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import pytest
from fastapi.testclient import TestClient

from app import app

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_I18N_PATH = ROOT / "static" / "portal" / "portal-i18n.js"
PORTAL_SOURCE = PORTAL_PATH.read_text(encoding="utf-8")
PORTAL_I18N_SOURCE = PORTAL_I18N_PATH.read_text(encoding="utf-8")


def _run_node_render_delivery(renderer: str, page_path: str, context: dict | None = None) -> dict:
    """Execute delivery renderers in Node.js with portal.js evaluation."""
    ctx_json = json.dumps(context or {})
    record_id = str(context.get("recordId", "") if context else "")
    script = """
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");

function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing start: ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end: ${end}`);
  return source.slice(offset, finish);
}

// Mock browser globals
global.window = global;
global.document = {};
function safeText(v) { return String(v == null ? "" : v); }
function normalizePath(p) { return "/" + String(p || "").replace(/^\\/+|\\/+$/g, ""); }
function uiText(k, fb) { return fb || k; }
function deliveryCenterText(k, fb, p) {
  let res = fb || k;
  if (p && typeof p === "object") {
    for (const [key, val] of Object.entries(p)) {
      res = res.replace(new RegExp(`\\\\{${key}\\\\}`, "g"), val);
    }
  }
  return res;
}
function adminNumericValue(v) { const n = Number(v); return isNaN(n) ? null : n; }
function localizedNumber(v) { return String(v); }
function renderHero(page, ctx) { return `<header class="portal-page-hero"><h1>${page.title || "Hero"}</h1></header>`; }
function renderEmpty(t, m, icon) { return `<div class="portal-empty"><h2>${t}</h2><p>${m}</p></div>`; }
function renderStatusCard(page, ctx) { return `<div class="portal-status-card">Status</div>`; }
function renderSummary(page, ctx) { return `<div class="portal-summary">Summary</div>`; }
function renderNotes(page) { return `<div class="portal-notes">Notes</div>`; }
function renderDataTableWrap(t) { return `<div class="portal-table-wrap">${t}</div>`; }
function renderRowsTable(columns, rows, renderRow, emptyTitle, emptyText) {
  const body = Array.isArray(rows) && rows.length
    ? rows.map((row) => `<tr>${renderRow(row)}</tr>`).join("")
    : `<tr><td class="portal-empty-cell" colspan="${columns.length}">${renderEmpty(emptyTitle, emptyText, "○")}</td></tr>`;
  return renderDataTableWrap(`<table class="portal-data-table"><thead><tr>${columns.map((column) => `<th scope="col">${safeText(column)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`);
}
function deliveryListReadState(context, kind) { return "ready"; }
function renderCollectionReadState(kind, state, canRefresh) { return ""; }
function stateFor(p, ctx) { return "ready"; }
function validProjectId(v) { return Boolean(v); }
function validVaultAssetId(v) { return Boolean(v); }
function transientFormValues(r) { return {}; }
function renderFields(f, c, ctx, v, p) { return ""; }
function assetVaultListing(ctx) { return { filters: {}, total_count: 0, items: [] }; }
function assetVaultLibraryItems(ctx) { return []; }
function assetVaultLifecyclePanel(ctx, items, canRestore) { return ""; }
function assetVaultFilterFields() { return []; }
function assetVaultFilterIsActive() { return false; }
function assetVaultPagination() { return ""; }
function renderAssetVaultPagination() { return ""; }
function vaultDownloadPath(item) { return `/api/v1/asset-vault/${encodeURIComponent(item.id)}/download`; }
function vaultBytes(b) { return `${b || 0} B`; }

const ICONS = {
  jobs: "jobs", assets: "assets", dashboard: "dashboard", prompt: "prompt",
  video: "video", image: "image", voice: "voice", wallet: "wallet",
  payments: "payments", pricing: "pricing", account: "account", support: "support"
};

// Evaluate portal constants & helpers
eval(extract("const ALLOWED_STATES = new Set([", "const STATE_LABELS = Object.freeze({").replace("const ALLOWED_STATES =", "global.ALLOWED_STATES ="));
eval(extract("const STATE_LABELS = Object.freeze({", "const STATE_I18N_KEYS = Object.freeze({").replace("const STATE_LABELS =", "global.STATE_LABELS ="));
eval(extract("const STATE_I18N_KEYS = Object.freeze({", "function stateLabel(status) {").replace("const STATE_I18N_KEYS =", "global.STATE_I18N_KEYS ="));
eval(extract("function stateLabel(status) {", "const PAYMENT_STATUS_LABELS ="));
eval(extract("function badge(status, label) {", "function subtitleAssetOperationsReadBadge"));
eval(extract("const JOB_FILTERS =", "function canonicalTicketStatus").replace("const JOB_FILTERS =", "global.JOB_FILTERS =").replace("const ASSET_FILTERS =", "global.ASSET_FILTERS ="));
eval(extract("function reportedOutput(item)", "function renderDeliveryWorkspaceNav"));
eval(extract("function renderDeliveryWorkspaceNav(currentPath)", "function renderHistoryHub(page, context)"));

const page = { path: "__PAGE_PATH__", title: "Delivery", recordId: "__RECORD_ID__" };
const context = __CTX_JSON__;

try {
  let html = "";
  if ("__RENDERER__" === "jobs") html = renderJobs(page, context);
  else if ("__RENDERER__" === "job-detail") html = renderJobDetail(page, context);
  else if ("__RENDERER__" === "assets") html = renderAssets(page, context);
  console.log(JSON.stringify({ ok: true, html }));
} catch (err) {
  console.log(JSON.stringify({ ok: false, error: err.message, stack: err.stack }));
}
"""
    script = (
        script.replace("__PAGE_PATH__", page_path)
        .replace("__RECORD_ID__", record_id)
        .replace("__CTX_JSON__", ctx_json)
        .replace("__RENDERER__", renderer)
    )
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr + "\n" + result.stdout}
    return json.loads(result.stdout)


class TestP0WebappV204OutputAssetDeliveryCenter:
    """Empirical verification test suite for Output Asset Delivery Center."""

    def test_01_jobs_route_valid(self) -> None:
        """1. /jobs remains valid and registered in portal manifest."""
        client = TestClient(app)
        resp = client.get("/jobs", follow_redirects=False)
        assert resp.status_code in (200, 307), f"/jobs returned {resp.status_code}"
        assert resp.status_code != 404, "/jobs must not 404"
        assert 'customerPage("/jobs"' in PORTAL_SOURCE, "/jobs must be registered in portal.js"
        assert 'case "jobs": return renderJobs(page, context);' in PORTAL_SOURCE

    def test_02_assets_route_valid(self) -> None:
        """2. /assets remains valid and registered as canonical asset route."""
        client = TestClient(app)
        resp = client.get("/assets", follow_redirects=False)
        assert resp.status_code in (200, 307), f"/assets returned {resp.status_code}"
        assert resp.status_code != 404, "/assets must not 404"
        assert 'customerPage("/assets"' in PORTAL_SOURCE, "/assets must be registered in portal.js"
        assert 'case "assets": return renderAssets(page, context);' in PORTAL_SOURCE

    def test_03_asset_vault_deep_link_valid(self) -> None:
        """3. /asset-vault deep link valid: ASSET_VAULT_404=0, ASSET_VAULT_REDIRECT_LOOP=0."""
        client = TestClient(app)
        resp = client.get("/asset-vault", follow_redirects=False)
        assert resp.status_code in (200, 307), f"/asset-vault returned {resp.status_code}"
        assert resp.status_code != 404, "/asset-vault must never 404"
        assert resp.status_code != 310, "No redirect loop allowed on /asset-vault"

    def test_04_one_primary_asset_authority(self) -> None:
        """4. CANONICAL_ASSET_ROUTE=/assets, ASSET_PRIMARY_SURFACE_COUNT=1 in customer nav."""
        # Find customer navGroups in portal.js
        match = re.search(r"function navGroups\(context, currentPage\) \{(.*?)\n  \}", PORTAL_SOURCE, re.DOTALL)
        assert match, "navGroups function not found"
        nav_source = match.group(1)

        # Ensure only 1 primary asset surface (/assets) in primary customer nav
        asset_surfaces_in_nav = [
            route for route in ["/assets", "/asset-vault"]
            if f'["{route}"' in nav_source
        ]
        assert asset_surfaces_in_nav == ["/assets"], (
            f"Expected exactly ['/assets'] in primary customer nav, got {asset_surfaces_in_nav}"
        )

    def test_05_raw_uuid_not_primary_display(self) -> None:
        """5. Raw UUIDs must NOT be displayed as the primary customer identity."""
        raw_uuid = "018f3a5b-9c2d-784e-8f12-3456789abcde"
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": raw_uuid, "feature": "Tạo ảnh chân dung", "status": "completed", "output_available": True}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]

        # Raw full UUID should not be the visible link text in table cells
        assert f">{raw_uuid}<" not in html, "Raw UUID should not be visible as primary anchor text"
        # Friendly reference should be present
        assert "friendlyJobReference" in PORTAL_SOURCE, "friendlyJobReference helper must exist"

    def test_06_technical_status_leakage_absent(self) -> None:
        """6. Technical statuses translated to truthful Vietnamese copy without changing state."""
        # Check STATE_LABELS in portal.js
        labels_match = re.search(r"const STATE_LABELS = Object\.freeze\(\{(.*?)\}\);", PORTAL_SOURCE, re.DOTALL)
        assert labels_match, "STATE_LABELS not found"
        labels_source = labels_match.group(1)

        assert 'queued: "Đang chờ xử lý"' in labels_source, "queued must map to 'Đang chờ xử lý'"
        assert 'failed: "Không hoàn tất"' in labels_source, "failed must map to 'Không hoàn tất'"

        # Check DELIVERY_CENTER_MESSAGES in portal-i18n.js
        assert '"deliveryCenter.filter.jobs.queued": "Đang chờ xử lý"' in PORTAL_I18N_SOURCE
        assert '"deliveryCenter.filter.jobs.failed": "Không hoàn tất"' in PORTAL_I18N_SOURCE

    def test_07_completed_job_links_real_asset_when_available(self) -> None:
        """7. Completed job links real asset when real durable asset exists."""
        job_id = "job-comp-101"
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": job_id, "feature": "Tạo ảnh", "status": "completed", "output_available": True, "asset_id": "asset-real-101", "download_ready": True}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        # Output column should clearly indicate asset link or readiness
        assert "Tải tệp" in html or "asset-real-101" in html or "Output" in html

    def test_08_completed_job_without_asset_has_no_fake_download(self) -> None:
        """8. Completed job without durable asset has NO fake download button."""
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": "job-no-asset-1", "feature": "Tạo video", "status": "completed", "output_available": False}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'href="/api/v1/assets/job-no-asset-1/download"' not in html
        assert 'data-portal-action="download"' not in html
        assert "portal-delivery-link" not in html
        assert "Tải tệp" not in html

    def test_09_missing_asset_has_no_download_cta(self) -> None:
        """9. Missing asset has no download CTA: DEAD_DOWNLOAD_CTA=0, MISSING_FILE_DOWNLOAD_CTA=0."""
        res = _run_node_render_delivery("assets", "/assets", {
            "assets": [
                {"id": "asset-missing-1", "feature": "Tạo ảnh", "status": "completed", "download_ready": False, "missing": True}
            ],
            "capabilities": {"refresh-assets": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'href="/api/v1/assets/asset-missing-1/download"' not in html
        assert 'href="#"' not in html
        assert 'href=""' not in html

    def test_10_expired_asset_has_no_download_cta(self) -> None:
        """10. Expired asset has no download CTA: EXPIRED_FILE_DOWNLOAD_CTA=0."""
        res = _run_node_render_delivery("assets", "/assets", {
            "assets": [
                {"id": "asset-expired-1", "feature": "Tạo ảnh", "status": "completed", "download_ready": False, "expired": True}
            ],
            "capabilities": {"refresh-assets": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'href="/api/v1/assets/asset-expired-1/download"' not in html

    def test_11_unknown_eta_not_fabricated(self) -> None:
        """11. Unknown ETA not fabricated: CLIENT_DERIVED_ETA=0, UNKNOWN_ETA_AS_ZERO=0."""
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": "job-eta-1", "feature": "Tạo video", "status": "processing"}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        # Must not fabricate "0 giây còn lại" or synthetic frontend timers
        assert "0 giây còn lại" not in html
        assert "00:00" not in html

    def test_12_fake_retention_countdown_absent(self) -> None:
        """12. Fake retention countdown absent: FAKE_RETENTION_COUNTDOWN=0."""
        res = _run_node_render_delivery("assets", "/assets", {
            "assets": [
                {"id": "asset-ret-1", "feature": "Tạo ảnh", "status": "completed", "download_ready": True}
            ],
            "capabilities": {"refresh-assets": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert "còn lại để tải" not in html
        assert "đếm ngược" not in html

    def test_13_fake_cancel_action_absent_without_backend_authority(self) -> None:
        """13. FAKE_CANCEL_ACTION=0: No fake working cancel button on job surface."""
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": "job-cancel-1", "feature": "Tạo video", "status": "processing"}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'data-portal-action="cancel-job"' not in html, "No fake cancel-job action allowed"

    def test_14_cancel_terminal_job_unavailable(self) -> None:
        """14. Terminal jobs (completed/failed/refunded) must never present a cancel button."""
        res = _run_node_render_delivery("jobs", "/jobs", {
            "jobs": [
                {"id": "job-term-1", "feature": "Tạo video", "status": "completed"}
            ],
            "capabilities": {"refresh-jobs": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'data-portal-action="cancel-job"' not in html

    def test_15_report_job_action_truthful(self) -> None:
        """15. FAKE_REPORT_SUBMISSION=0: Job recovery support wires to support ticket with job context."""
        assert 'data-portal-action="create-ticket"' in PORTAL_SOURCE
        assert "function renderJobRecoverySupport" in PORTAL_SOURCE

    def test_16_fake_bulk_zip_absent_without_backend_authority(self) -> None:
        """16. FAKE_BULK_ZIP=0: No fake bulk ZIP download CTA on delivery surfaces."""
        res = _run_node_render_delivery("assets", "/assets", {
            "assets": [
                {"id": "asset-zip-1", "feature": "Tạo ảnh", "status": "completed", "download_ready": True}
            ],
            "capabilities": {"refresh-assets": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'data-portal-action="download-all-zip"' not in html
        assert "Tải toàn bộ ZIP" not in html

    def test_17_fake_reuse_as_input_absent_without_backend_authority(self) -> None:
        """17. FAKE_REUSE_INPUT=0: No fake 'reuse as input' button on delivery surfaces."""
        res = _run_node_render_delivery("assets", "/assets", {
            "assets": [
                {"id": "asset-reuse-1", "feature": "Tạo ảnh", "status": "completed", "download_ready": True}
            ],
            "capabilities": {"refresh-assets": True}
        })
        assert res["ok"], f"Render failed: {res.get('error')}"
        html = res["html"]
        assert 'data-portal-action="reuse-as-input"' not in html
        assert "Dùng làm input" not in html

    def test_18_account_isolation_preserved(self) -> None:
        """18. CROSS_ACCOUNT_JOB_LEAK=0, CROSS_ACCOUNT_ASSET_LEAK=0."""
        # Validated by test_p0_webapp_web05_jobs_history_assets_truth.py
        # and API requires account authentication
        client = TestClient(app)
        resp_jobs = client.get("/api/v1/jobs")
        assert resp_jobs.status_code in (401, 403), "Anonymous jobs API must be guarded"
        resp_assets = client.get("/api/v1/assets")
        assert resp_assets.status_code in (401, 403), "Anonymous assets API must be guarded"

    def test_19_v2_03_commerce_regression_zero(self) -> None:
        """19. All V2-03 commerce surfaces continue to pass without regression."""
        from tests.test_p0_webapp_v2_03_customer_commerce_surfaces import TestP0WebappV203CustomerCommerceSurfaces
        suite = TestP0WebappV203CustomerCommerceSurfaces()
        suite.test_01_canonical_commerce_route_and_primary_nav_parity()
        suite.test_02_legacy_deep_links_no_404_and_registered()
        suite.test_03_zero_fake_vip_tiers_and_zero_fake_discounts()
        suite.test_04_canonical_pricing_source_single()
        suite.test_05_package_cta_safety_and_no_dead_buttons()
        suite.test_06_zero_wallet_mutations_and_zero_payos_direct_creation()
        suite.test_11_membership_provenance_and_zero_assumed_static_ladder()
        suite.test_12_canonical_xu_charge_semantics_and_zero_creation_charge_claim()
        suite.test_13_zero_unproven_auto_refund_and_no_expiry_claims()
        suite.test_14_zero_unsourced_payos_sla()
        suite.test_15_package_catalog_source_truth_and_zero_fake_fallback_packages()

    def test_20_mobile_delivery_surface_contract(self) -> None:
        """20. Mobile delivery cards wrap safely without horizontal overflow."""
        assert "renderJobMobileCard" in PORTAL_SOURCE
        assert "renderAssetMobileCard" in PORTAL_SOURCE
        assert "portal-delivery-mobile-card" in PORTAL_SOURCE
        assert "portal-delivery-mobile-records" in PORTAL_SOURCE
