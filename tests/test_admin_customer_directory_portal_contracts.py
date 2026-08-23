"""Focused contracts for the redacted Web Admin customer directory UI."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import copyfast_admin_erp_navigation as nav
from copyfast_pages import _PORTAL_BUILD_SOURCE_FILES


ROOT = Path(__file__).resolve().parents[1]
ALPHA_ID = "00000000-0000-4000-8000-000000000001"
TELEGRAM_ID = "00000000-0000-4000-8000-000000000002"
MODULE_JS = ROOT / "static" / "portal" / "admin-customer-directory.js"
PORTAL_JS = ROOT / "static" / "portal" / "portal.js"
INTEGRATION_JS = ROOT / "static" / "portal" / "integration.js"
SHELL_HTML = ROOT / "templates" / "portal_shell.html"
APP_PY = ROOT / "app.py"


def _run_node_harness(script: str) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for Portal JavaScript contract execution")
    res = subprocess.run([node, "-e", script], capture_output=True, text=True, cwd=str(ROOT))
    if res.returncode != 0:
        raise RuntimeError(f"Node execution failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}")
    return json.loads(res.stdout) if res.stdout.strip() else {}


def test_asset_order_and_file_budgets() -> None:
    assert MODULE_JS.exists(), "admin-customer-directory.js must exist"
    assert "admin-customer-directory.js" in _PORTAL_BUILD_SOURCE_FILES
    html_text = SHELL_HTML.read_text(encoding="utf-8")
    mod_pos = html_text.find("admin-customer-directory.js")
    motion_pos = html_text.find("portal-motion.js")
    portal_pos = html_text.find("portal.js")
    integration_pos = html_text.find("integration.js")
    assert motion_pos < mod_pos < portal_pos < integration_pos
    mod_lines = len(MODULE_JS.read_text(encoding="utf-8").splitlines())
    test_lines = len(Path(__file__).read_text(encoding="utf-8").splitlines())
    assert mod_lines <= 300, f"Module JS is {mod_lines} lines (max 300)"
    assert test_lines <= 400, f"Test file is {test_lines} lines (max 400)"


def test_pure_ui_module_node_contracts() -> None:
    script = r'''
    const fs = require("fs");
    const path = require("path");
    const modSource = fs.readFileSync(path.join(process.cwd(), "static/portal/admin-customer-directory.js"), "utf8");
    const window = {};
    eval(modSource);
    const mod = window.TOANAASAdminCustomerDirectory;
    if (!mod || typeof mod !== "object" || !Object.isFrozen(mod)) throw new Error("Export must be frozen object");
    if (mod.LIST_ROUTE !== "/admin/customers") throw new Error("Invalid LIST_ROUTE");
    if (!mod.isRoute("/admin/customers") || !mod.isRoute("/admin/customers/00000000-0000-4000-8000-000000000001")) throw new Error("isRoute failed");
    if (mod.isRoute("/admin/users") || mod.isRoute("/admin/customers/not-uuid")) throw new Error("isRoute false positive");
    if (mod.accountIdFromPath("/admin/customers/00000000-0000-4000-8000-000000000001") !== "00000000-0000-4000-8000-000000000001") throw new Error("accountIdFromPath failed");
    if (mod.accountIdFromPath("/admin/customers/invalid") !== "") throw new Error("accountIdFromPath fail-closed failed");

    const empty = mod.emptyState();
    if (!Array.isArray(empty.items) || empty.customer !== null || empty.readState !== "loading") throw new Error("Invalid emptyState");
    if (mod.listPath({ q: "test", status: "active" }, 50) !== "/admin/customers?q=test&status=active&limit=25&offset=50") throw new Error("listPath failed");
    if (mod.detailPath("00000000-0000-4000-8000-000000000001") !== "/admin/customers/00000000-0000-4000-8000-000000000001") throw new Error("detailPath failed");

    const sampleRawList = {
      source: "web_accounts_redacted",
      customers: [{
        id: "00000000-0000-4000-8000-000000000001",
        display_name: "<script>alert(1)</script>Alpha",
        email: "alpha@example.com",
        account_type: "standard",
        role: "user",
        role_label: "Khách hàng",
        status: "active",
        password_login_enabled: true,
        telegram_linked: false,
        profile: { locale: "vi", timezone: "Asia/Ho_Chi_Minh", avatar_style: "gradient" },
        created_at: "2026-01-05T00:00:00Z",
        updated_at: "2026-01-05T01:00:00Z"
      }],
      returned: 1, limit: 25, offset: 0, has_more: false, next_offset: null,
      filters: { q: "", status: "all" }
    };
    const normList = mod.normalizeList(sampleRawList);
    if (!normList || normList.customers.length !== 1) throw new Error("normalizeList failed");

    const sampleRawDetail = {
      source: "web_accounts_redacted",
      customer: sampleRawList.customers[0]
    };
    const normDetail = mod.normalizeDetail(sampleRawDetail);
    if (!normDetail || normDetail.customer.id !== sampleRawList.customers[0].id) throw new Error("normalizeDetail failed");

    // Defect 1 & Corrective R2: Check exact schema via public normalizeList and normalizeDetail
    const expectsThrow = (payload, normalizer, msg) => {
      try {
        normalizer(payload);
        throw new Error("Did not throw on: " + msg);
      } catch (e) {
        if (e.message.startsWith("Did not throw on")) throw e;
      }
    };

    // clone payload cases
    let testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].display_name = 123;
    expectsThrow(testPayload, mod.normalizeList, "display_name number");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    delete testPayload.customers[0].email;
    expectsThrow(testPayload, mod.normalizeList, "missing customer key email");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].password_hash = "secret";
    expectsThrow(testPayload, mod.normalizeList, "extra customer key password_hash");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].profile = [];
    expectsThrow(testPayload, mod.normalizeList, "profile array");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].profile.extra = "value";
    expectsThrow(testPayload, mod.normalizeList, "extra profile key");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].account_type = "invalid";
    expectsThrow(testPayload, mod.normalizeList, "invalid account_type");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].role = "super_admin";
    expectsThrow(testPayload, mod.normalizeList, "invalid role");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.customers[0].status = "unknown";
    expectsThrow(testPayload, mod.normalizeList, "invalid status");

    // Pagination/Envelope checks
    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.returned = "1";
    expectsThrow(testPayload, mod.normalizeList, "returned string");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.returned = 2; // mismatch length
    expectsThrow(testPayload, mod.normalizeList, "returned mismatch customers length");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.limit = 101;
    expectsThrow(testPayload, mod.normalizeList, "limit out of bounds");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.offset = -1;
    expectsThrow(testPayload, mod.normalizeList, "offset out of bounds");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.has_more = "false";
    expectsThrow(testPayload, mod.normalizeList, "has_more string");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.next_offset = 10001;
    expectsThrow(testPayload, mod.normalizeList, "next_offset out of bounds");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.filters.q = 123;
    expectsThrow(testPayload, mod.normalizeList, "filters q number");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.filters.status = "unknown";
    expectsThrow(testPayload, mod.normalizeList, "filters status invalid");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.filters.extra = 1;
    expectsThrow(testPayload, mod.normalizeList, "filters extra key");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    delete testPayload.filters.q;
    expectsThrow(testPayload, mod.normalizeList, "filters missing q");

    testPayload = JSON.parse(JSON.stringify(sampleRawList));
    testPayload.extra_root_key = "1";
    expectsThrow(testPayload, mod.normalizeList, "extra root key in list envelope");

    let detailPayload = JSON.parse(JSON.stringify(sampleRawDetail));
    detailPayload.extra_root_key = "1";
    expectsThrow(detailPayload, mod.normalizeDetail, "extra root key in detail envelope");

    const helpers = {
      safeText: (v) => String(v || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"),
      badge: (s) => `<span class="portal-badge">${s}</span>`,
      renderHero: (p) => `<header class="portal-hero"><h1>${p.title}</h1></header>`,
      renderEmpty: (t, m) => `<div class="portal-empty"><h2>${t}</h2><p>${m}</p></div>`
    };

    const renderedList = mod.render(
      { path: "/admin/customers", title: "Khách hàng Web", layout: "admin-customer-directory" },
      { adminCustomerDirectory: { ...empty, items: normList.customers, readState: "ready", pagination: { limit: 25, offset: 0, returned: 1, has_more: false, next_offset: null } } },
      helpers
    );
    if (renderedList.includes("<script>")) throw new Error("XSS vulnerability in rendered list");
    if (!renderedList.includes("&lt;script&gt;alert(1)&lt;/script&gt;Alpha")) throw new Error("Escaped text missing in list");
    if (!renderedList.includes('tabindex="0"') || !renderedList.includes('data-portal-table-scroll')) throw new Error("Accessible scroll wrapper missing");
    if (!renderedList.includes("standard")) throw new Error("Missing account_type in list output"); // Defect 4

    const renderedDetail = mod.render(
      { path: "/admin/customers/:id", routePath: "/admin/customers/00000000-0000-4000-8000-000000000001", recordId: "00000000-0000-4000-8000-000000000001", title: "Chi tiết khách hàng Web", layout: "admin-customer-directory-detail" },
      { adminCustomerDirectory: { ...empty, customer: normDetail.customer, readState: "ready" } },
      helpers
    );
    if (renderedDetail.includes("<script>")) throw new Error("XSS vulnerability in rendered detail");
    if (!renderedDetail.includes("&lt;script&gt;alert(1)&lt;/script&gt;Alpha")) throw new Error("Escaped text missing in detail");
    if (!renderedDetail.includes("<dt class=") || !renderedDetail.includes("<dd class=")) throw new Error("Missing semantic dl/dt/dd in detail"); // Defect 4

    const renderedEmpty = mod.render(
      { path: "/admin/customers", title: "Khách hàng Web", layout: "admin-customer-directory" },
      { adminCustomerDirectory: { ...empty, items: [], readState: "ready", pagination: { limit: 25, offset: 0, returned: 0, has_more: false, next_offset: null } } },
      helpers
    );
    if (renderedEmpty.includes('class="portal-card portal-card-pad"><div class="portal-empty"')) throw new Error("Nested portal-card in empty state"); // Defect 4

    console.log(JSON.stringify({ ok: true, listLength: renderedList.length, detailLength: renderedDetail.length }));
    '''
    out = _run_node_harness(script)
    assert out.get("ok") is True


def test_app_local_admin_route_guards() -> None:
    app_source = APP_PY.read_text(encoding="utf-8")
    assert "/admin/customers" in app_source
    assert 'normalized.startswith("/admin/customers/")' in app_source
    assert 'import copyfast_admin_customer_directory' in app_source
    assert 'app.include_router(copyfast_admin_customer_directory.router)' in app_source


def test_navigation_metadata_web_private_crm() -> None:
    groups = nav.web_local_admin_groups()
    crm_group = next((g for g in groups if g["id"] == "web_private_crm"), None)
    assert crm_group is not None, "web_private_crm group must exist"
    cust_mod = next((m for m in crm_group["modules"] if m["id"] == "customer_directory"), None)
    assert cust_mod is not None, "customer_directory module must exist in web_private_crm"
    assert cust_mod["route"] == "/admin/customers"
    assert cust_mod["authority"] == "web_local_admin"
    assert cust_mod["source"] == "web_native"
    assert cust_mod["capability"] == "redacted_web_account_directory_read_only"
    assert "customer_directory" in nav._MODULE_DESCRIPTIONS


def test_portal_registration_and_no_motion_conditions() -> None:
    portal_text = PORTAL_JS.read_text(encoding="utf-8")
    assert 'adminPage("/admin/customers"' in portal_text
    assert 'case "admin-customer-directory":' in portal_text
    assert 'case "admin-customer-directory-detail":' in portal_text
    assert '/admin/customers' in portal_text
    assert 'isCustomerDirectoryRoute' in portal_text or 'admin/customers' in portal_text
    assert 'adminPage("/admin/users"' in portal_text, "Bot admin users must remain"


def test_integration_fences_and_actions() -> None:
    integration_text = INTEGRATION_JS.read_text(encoding="utf-8")
    assert "isNativeAdminCustomerDirectoryPath" in integration_text
    assert "adminCustomerDirectorySessionEpoch" in integration_text or "customerDirectory" in integration_text
    assert "admin-customer-filter" in integration_text
    assert "admin-customer-clear" in integration_text
    assert "admin-customer-page" in integration_text
    assert "admin-customer-refresh" in integration_text
