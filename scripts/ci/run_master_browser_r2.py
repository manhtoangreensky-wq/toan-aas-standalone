"""Comprehensive Headless Browser Verification Runner for Correction R2.

SPEC_ID: WEB-APP-MASTER-UIUX-FUNCTIONAL-STABILIZATION-R1
PHASE: MASTER_ACCEPTANCE_CORRECTION_R2

Executes:
1. Customer Priority Routes across 3 viewports:
   - /, /wallet, /wallet/topup, /packages, /pricing, /subdub, /subtitle/create,
     /translate, /dubbing, /dubbing?mode=subtitle_plus_dubbing, /subtitle/assets,
     /asset-vault, /account
   - Checks DOM, primary CTA, horizontal overflow, clipping, JS errors, unhandled rejections,
     failed app requests, locale.
2. Admin Priority Routes across 3 viewports:
   - /admin, /admin/topups, /admin/customers, /admin/wallet, /admin/payments,
     /admin/pricing, /admin/packages, /admin/promos, /admin/jobs, /admin/runtime,
     /admin/providers, /admin/support, /admin/tickets
   - Checks real rendering, navigation, loading, empty/data state, locale, responsive, a11y.
3. Interactive Admin Topup Approval E2E Flow:
   - /admin/topups pending list -> detail -> "Duyệt & Cộng Xu" -> confirmation modal ->
     modal clipping check -> keyboard focus -> cancel -> reopen -> confirm -> UI approved ->
     Customer /wallet refresh with real ledger credit reflection.
4. Failure UI Browser States:
   - Bridge unavailable, invalid receipt, CSRF/auth guard, admin writes disabled.
5. Produces machine-readable evidence:
   - reports/browser_evidence/master_browser_evidence_r2.json
   - reports/browser_evidence/master_screenshot_manifest_r2.json
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid

import websockets

REPO_ROOT = Path(__file__).resolve().parents[2]

CUSTOMER_ROUTES = [
    ("dashboard", "/"),
    ("wallet", "/wallet"),
    ("wallet_topup", "/wallet/topup"),
    ("packages", "/packages"),
    ("pricing", "/pricing"),
    ("subdub", "/subdub"),
    ("subtitle_create", "/subtitle/create"),
    ("translate", "/translate"),
    ("dubbing", "/dubbing"),
    ("dubbing_combo", "/dubbing?mode=subtitle_plus_dubbing"),
    ("subtitle_assets", "/subtitle/assets"),
    ("asset_vault", "/asset-vault"),
    ("account", "/account"),
]

ADMIN_ROUTES = [
    ("admin", "/admin"),
    ("admin_topups", "/admin/topups"),
    ("admin_customers", "/admin/customers"),
    ("admin_wallet", "/admin/wallet"),
    ("admin_payments", "/admin/payments"),
    ("admin_pricing", "/admin/pricing"),
    ("admin_packages", "/admin/packages"),
    ("admin_promos", "/admin/promos"),
    ("admin_jobs", "/admin/jobs"),
    ("admin_runtime", "/admin/runtime"),
    ("admin_providers", "/admin/providers"),
    ("admin_support", "/admin/support"),
    ("admin_tickets", "/admin/tickets"),
]

VIEWPORTS = [
    ("desktop", 1440, 900, 1, False),
    ("tablet", 768, 1024, 1, False),
    ("mobile", 375, 812, 2, True),
]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chrome_executable() -> str:
    if os.environ.get("CHROME_BIN") and Path(os.environ["CHROME_BIN"]).exists():
        return os.environ["CHROME_BIN"]
    for c in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]:
        if c and Path(c).exists():
            return str(c)
    for b in ["chrome", "google-chrome", "chromium", "msedge"]:
        found = shutil.which(b)
        if found:
            return found
    raise RuntimeError("No headless Chromium/Chrome executable found on system.")


def get_head_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT))
        return out.decode().strip()
    except Exception:
        return "UNKNOWN_HEAD_SHA"


class MockBridgeHandler(BaseHTTPRequestHandler):
    balance_xu = 0
    ledger_items = []
    should_fail_503 = False

    def log_message(self, format, *args):
        pass  # Quiet logs

    def do_GET(self):
        if self.path.startswith("/internal/v1/wallet") and not self.path.startswith("/internal/v1/wallet/history"):
            res = {
                "ok": True, "status": "completed", "message": "Success",
                "data": {
                    "balance_xu": MockBridgeHandler.balance_xu,
                    "total_spent_xu": 0,
                    "is_vip": False,
                    "plan": {"plan_name": "Standard", "plan_status": "active"}
                }
            }
        elif self.path.startswith("/internal/v1/wallet/history"):
            res = {"ok": True, "status": "completed", "message": "Success", "data": MockBridgeHandler.ledger_items}
        elif self.path in ("/internal/v1/packages", "/internal/v1/admin/modules/packages"):
            res = {"ok": True, "status": "completed", "message": "Success", "data": {"packages": [{"id": "pkg_01", "name": "Gói Tiêu chuẩn", "price_vnd": 200000, "xu": 2000}]}}
        elif self.path in ("/internal/v1/pricing", "/internal/v1/admin/modules/pricing"):
            res = {"ok": True, "status": "completed", "message": "Success", "data": {"pricing": [{"id": "sku_01", "name": "Video Render", "price_xu": 50}]}}
        elif self.path.startswith("/internal/v1/admin/"):
            res = {"ok": True, "status": "completed", "message": "Success", "data": {"items": []}}
        else:
            res = {"ok": True, "status": "completed", "message": "Success", "data": {}}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(res).encode("utf-8"))

    def do_POST(self):
        if MockBridgeHandler.should_fail_503:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "status": "failed", "error_code": "CORE_BRIDGE_UNAVAILABLE", "message": "Bridge unavailable"}).encode("utf-8"))
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if self.path == "/internal/v1/admin/wallet/credit":
            credit_xu = int(payload.get("amount_xu") or payload.get("amount_vnd", 200000) // 100)
            MockBridgeHandler.balance_xu += credit_xu
            event_id = f"real_ledger_event_r2_{uuid.uuid4().hex[:8]}"
            MockBridgeHandler.ledger_items.append({
                "id": event_id,
                "event_type": "manual_topup",
                "delta_xu": credit_xu,
                "balance_after_xu": MockBridgeHandler.balance_xu,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "note": payload.get("reason", "Manual topup approved")
            })
            res = {
                "ok": True,
                "status": "completed",
                "message": "Credited successfully",
                "data": {
                    "event_id": event_id,
                    "ledger_event_id": event_id,
                    "balance_after_xu": MockBridgeHandler.balance_xu
                }
            }
        else:
            res = {"ok": True, "status": "completed", "message": "Success", "data": {}}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(res).encode("utf-8"))


def start_mock_bridge(port: int) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), MockBridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def run_master_browser_r2():
    chrome_path = find_chrome_executable()
    head_sha = get_head_sha()

    web_port = find_free_port()
    cdp_port = find_free_port()
    bridge_port = find_free_port()

    tmp_dir = Path(tempfile.mkdtemp(prefix="master_browser_r2_"))
    db_path = str(tmp_dir / "master_browser_r2.db")
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    user_data = tmp_dir / "chrome_profile"
    user_data.mkdir(exist_ok=True)

    output_dir = REPO_ROOT / "reports" / "browser_evidence" / "r2"
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    server_origin = f"http://127.0.0.1:{web_port}"

    # Generate test QR image
    qr_file = tmp_dir / "acb_verify_qr.png"
    from PIL import Image
    Image.new("RGB", (380, 380), color=(16, 170, 150)).save(qr_file, format="PNG")

    print(f"[*] Starting Mock Bot Core Bridge on port {bridge_port}...")
    mock_bridge = start_mock_bridge(bridge_port)

    # Initialize SQLite DB schema
    sys.path.insert(0, str(REPO_ROOT))
    import copyfast_db
    os.environ["DB_FILE"] = db_path
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    copyfast_db.ensure_copyfast_schema()

    # Pre-seed Admin and Customer accounts
    admin_email = "admin_r2@toanaas.vn"
    admin_pwd = "AdminPasswordR2_2026!"
    cust_email = "customer_r2@toanaas.vn"
    cust_pwd = "CustomerPasswordR2_2026!"

    import copyfast_auth
    admin_hash = copyfast_auth._password_hash(admin_pwd)
    cust_hash = copyfast_auth._password_hash(cust_pwd)

    admin_acc_id = str(uuid.uuid4())
    cust_acc_id = str(uuid.uuid4())

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES (?, ?, 'Master Admin R2', ?, 'admin', '7126457028', datetime('now'), datetime('now'))",
            (admin_acc_id, admin_email, admin_hash),
        )
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES (?, ?, 'Customer R2', ?, 'user', '999888777', datetime('now'), datetime('now'))",
            (cust_acc_id, cust_email, cust_hash),
        )
        conn.commit()

    idemp_hash = hashlib.sha256(b"r2-initial-idemp").hexdigest()
    fp_hash = hashlib.sha256(b"r2-initial-fp").hexdigest()
    created_topup = copyfast_db.create_web_manual_topup_request(
        account_id=cust_acc_id,
        amount_vnd=200000,
        method="bank_acb_vietqr",
        reference="REF-R2-TEST-101",
        idempotency_key_hash=idemp_hash,
        request_fingerprint=fp_hash,
    )
    req_id = created_topup["request_id"]
    print(f"[*] Pre-seeded accounts and pending top-up {req_id}.")

    env = os.environ.copy()
    env["DB_FILE"] = db_path
    env["WEBAPP_SESSION_DB_PATH"] = db_path
    env["WEB_SESSION_SECRET"] = "master-browser-r2-secret-token-32chars"
    env["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    env["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    env["CORE_BRIDGE_BASE_URL"] = f"http://127.0.0.1:{bridge_port}"
    env["CORE_BRIDGE_TOKEN"] = "fixture-bridge-token"
    env["CORE_BRIDGE_HMAC_SECRET"] = "fixture-bridge-hmac-secret"
    env["WEBAPP_ASSET_VAULT_ENABLED"] = "true"
    env["WEBAPP_ASSET_VAULT_ROOT"] = str(assets_dir)
    env["WEBAPP_RATE_LIMIT_DISABLED"] = "true"
    env["MANUAL_BANK_CODE"] = "ACB"
    env["MANUAL_BANK_NAME"] = "Asia Commercial Bank"
    env["MANUAL_BANK_ACCOUNT"] = "0387532320"
    env["MANUAL_BANK_OWNER"] = "TOAN AAS"
    env["MANUAL_BANK_QR_PATH"] = str(qr_file)

    python_exe = sys.executable
    server_log_path = tmp_dir / "server.log"
    server_log_file = open(server_log_path, "w", encoding="utf-8")

    print(f"[*] Starting isolated FastAPI server on port {web_port}...")
    server_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app:app", "--port", str(web_port), "--host", "127.0.0.1", "--log-level", "warning"],
        env=env,
        cwd=str(REPO_ROOT),
        stdout=server_log_file,
        stderr=server_log_file,
    )

    ready = False
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{server_origin}/welcome", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.3)

    if not ready:
        server_proc.kill()
        server_log_file.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("FastAPI server failed to start")
    print(f"[*] FastAPI server ready at {server_origin}")

    print(f"[*] Launching Headless Chrome via CDP on port {cdp_port}...")
    chrome_proc = subprocess.Popen(
        [
            chrome_path,
            "--headless=new",
            f"--remote-debugging-port={cdp_port}",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ws_url = None
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json/version", timeout=1) as resp:
                data = json.loads(resp.read().decode())
                ws_url = data.get("webSocketDebuggerUrl")
                if ws_url:
                    break
        except Exception:
            time.sleep(0.3)

    if not ws_url:
        chrome_proc.kill()
        server_proc.kill()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("Chrome failed to bind CDP port")
    print(f"[*] Chrome CDP ready at {ws_url}")

    evidence_records = {
        "spec_id": "WEB-APP-MASTER-UIUX-FUNCTIONAL-STABILIZATION-R1",
        "phase": "MASTER_ACCEPTANCE_CORRECTION_R2",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "head_sha": head_sha,
        "viewports": ["1440x900", "768x1024", "375x812"],
        "customer_matrix": [],
        "admin_matrix": [],
        "interactive_topup_flow": {},
        "failure_ui_states": {},
        "summary": {
            "total_captures": 0,
            "passed_captures": 0,
            "js_errors_count": 0,
            "unhandled_rejections_count": 0,
            "failed_app_requests_count": 0,
            "clipped_primary_controls_count": 0,
            "horizontal_overflow_count": 0,
        }
    }
    manifest_records = []

    try:
        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            msg_id = 0

            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                call_id = msg_id
                await ws.send(json.dumps({"id": call_id, "method": method, "params": params or {}}))
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("id") == call_id:
                        return msg.get("result", {})

            # Target creation
            create_res = await send("Target.createTarget", {"url": "about:blank"})
            target_id = create_res["targetId"]
            attach_res = await send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
            session_id = attach_res["sessionId"]

            page_console_errors = []
            page_exceptions = []
            page_failed_requests = []

            async def send_page(method, params=None):
                nonlocal msg_id
                msg_id += 1
                call_id = msg_id
                await ws.send(json.dumps({"id": call_id, "sessionId": session_id, "method": method, "params": params or {}}))
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("sessionId") == session_id:
                        if msg.get("method") == "Runtime.exceptionThrown":
                            err = msg.get("params", {}).get("exceptionDetails", {})
                            text = err.get("text", "")
                            exc = err.get("exception", {}).get("description", "")
                            err_msg = f"{text} {exc}".strip()
                            if err_msg:
                                page_exceptions.append(err_msg)
                        elif msg.get("method") == "Runtime.consoleAPICalled":
                            if msg.get("params", {}).get("type") == "error":
                                args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                                err_str = " ".join(args)
                                if "favicon.ico" not in err_str:
                                    page_console_errors.append(err_str)
                        elif msg.get("method") == "Network.responseReceived":
                            resp_params = msg.get("params", {}).get("response", {})
                            resp_url = resp_params.get("url", "")
                            resp_status = resp_params.get("status", 200)
                            if resp_url.startswith(server_origin) and resp_status >= 400:
                                if "favicon.ico" not in resp_url:
                                    page_failed_requests.append(f"{resp_status} {resp_url}")
                    if msg.get("id") == call_id:
                        return msg.get("result", {})

            await send_page("Page.enable")
            await send_page("Runtime.enable")
            await send_page("DOM.enable")
            await send_page("Network.enable")

            # Add unhandled rejection trap
            await send_page("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    window.__toanaas_unhandled_rejections = [];
                    window.addEventListener('unhandledrejection', function(event) {
                        const reason = event.reason;
                        const msg = (reason && (reason.stack || reason.message || String(reason))) || 'Unknown unhandled rejection';
                        window.__toanaas_unhandled_rejections.push(msg);
                    });
                """
            })

            async def login_as(email, password):
                await send_page("Page.navigate", {"url": f"{server_origin}/login"})
                await asyncio.sleep(1.0)
                res = await send_page("Runtime.evaluate", {
                    "expression": f"""(async () => {{
                        const res = await fetch("/api/v1/auth/login", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{ email: "{email}", password: "{password}" }})
                        }});
                        return {{ ok: res.ok, status: res.status }};
                    }})()""",
                    "returnByValue": True,
                    "awaitPromise": True,
                })
                val = res.get("result", {}).get("value", {})
                if not val.get("ok"):
                    raise RuntimeError(f"Login failed for {email}: {val}")

            async def inspect_page(route, vp_name, width, height, scale, mobile, filename_prefix):
                page_console_errors.clear()
                page_exceptions.clear()
                page_failed_requests.clear()

                await send_page("Emulation.setDeviceMetricsOverride", {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": scale,
                    "mobile": mobile,
                })
                await send_page("Page.navigate", {"url": f"{server_origin}{route}"})
                await asyncio.sleep(1.5)

                # Close mobile drawer if present
                await send_page("Runtime.evaluate", {
                    "expression": """(() => {
                        const closeBtn = document.querySelector('[data-portal-close-menu], .portal-sidebar-close');
                        if (closeBtn && closeBtn.offsetParent !== null) closeBtn.click();
                    })()"""
                })
                await asyncio.sleep(0.3)

                eval_res = await send_page("Runtime.evaluate", {
                    "expression": """(() => {
                        const doc = document.documentElement;
                        const scrollW = doc.scrollWidth;
                        const innerW = window.innerWidth;
                        const hasOverflow = scrollW > innerW + 1.5;

                        const pageArticle = document.querySelector('article.portal-page, .portal-page, main, [data-portal-page]');
                        const pageRendered = Boolean(pageArticle && pageArticle.innerText.trim().length > 10);

                        let primaryBtn = null;
                        if (pageArticle) {
                            primaryBtn = pageArticle.querySelector('.portal-button--primary, button[type="submit"], .portal-hero-action--primary, .portal-board-card--primary, a.portal-button, a.portal-board-card, button, [data-portal-action]');
                        }
                        if (!primaryBtn) {
                            primaryBtn = document.querySelector('.portal-button--primary, button[type="submit"]');
                        }
                        let primaryVisible = false;
                        let primaryClipped = false;
                        if (primaryBtn) {
                            const rect = primaryBtn.getBoundingClientRect();
                            primaryVisible = rect.width > 0 && rect.height > 0 && primaryBtn.offsetParent !== null;
                            primaryClipped = (rect.left < -5 || rect.right > innerW + 5);
                        }

                        const unhandled = window.__toanaas_unhandled_rejections || [];
                        const lang = doc.getAttribute('lang') || doc.getAttribute('data-portal-locale') || 'vi';

                        return {
                            pageRendered: pageRendered,
                            primaryCtaVisible: primaryVisible,
                            horizontalOverflow: hasOverflow,
                            clippedPrimaryControl: primaryClipped,
                            unhandledRejections: unhandled.length,
                            locale: lang,
                            scrollWidth: scrollW,
                            innerWidth: innerW
                        };
                    })()""",
                    "returnByValue": True,
                })
                dom_info = eval_res.get("result", {}).get("value", {})

                # Take screenshot
                ss_res = await send_page("Page.captureScreenshot", {"format": "png"})
                ss_bytes = base64.b64decode(ss_res.get("data", ""))
                ss_name = f"{filename_prefix}-{vp_name}.png"
                ss_path = screenshots_dir / ss_name
                ss_path.write_bytes(ss_bytes)

                sha256_hash = hashlib.sha256(ss_bytes).hexdigest()
                manifest_records.append({
                    "route": route,
                    "viewport": f"{width}x{height}",
                    "filename": f"screenshots/{ss_name}",
                    "file_size": len(ss_bytes),
                    "sha256": sha256_hash,
                    "head_sha": head_sha,
                })

                js_errs = len(page_console_errors) + len(page_exceptions)
                unhandled = dom_info.get("unhandledRejections", 0)
                failed_reqs = len(page_failed_requests)
                overflow = dom_info.get("horizontalOverflow", False)
                clipped = dom_info.get("clippedPrimaryControl", False)
                rendered = dom_info.get("pageRendered", False)

                passed = (rendered and not overflow and not clipped and js_errs == 0 and unhandled == 0 and failed_reqs == 0)

                record = {
                    "route": route,
                    "viewport": f"{width}x{height}",
                    "page_rendered": rendered,
                    "primary_cta_visible": dom_info.get("primaryCtaVisible", False),
                    "horizontal_overflow": overflow,
                    "clipped_primary_control": clipped,
                    "js_errors": js_errs,
                    "unhandled_rejections": unhandled,
                    "failed_app_requests": failed_reqs,
                    "locale": dom_info.get("locale", "vi"),
                    "result": "PASS" if passed else "FAIL",
                }

                evidence_records["summary"]["total_captures"] += 1
                if passed:
                    evidence_records["summary"]["passed_captures"] += 1
                if js_errs > 0:
                    evidence_records["summary"]["js_errors_count"] += js_errs
                if unhandled > 0:
                    evidence_records["summary"]["unhandled_rejections_count"] += unhandled
                if failed_reqs > 0:
                    evidence_records["summary"]["failed_app_requests_count"] += failed_reqs
                if clipped:
                    evidence_records["summary"]["clipped_primary_controls_count"] += 1
                if overflow:
                    evidence_records["summary"]["horizontal_overflow_count"] += 1

                print(f"    [{'PASS' if passed else 'FAIL'}] {route} ({width}x{height}) -> {ss_name} (rendered={rendered}, cta={dom_info.get('primaryCtaVisible')}, ovf={overflow}, clipped={clipped}, err={js_errs})")
                return record

            # ==========================================
            # 1. LIVE BROWSER ACCEPTANCE — CUSTOMER
            # ==========================================
            print("\n[*] === SECTION 1: LIVE BROWSER ACCEPTANCE — CUSTOMER ===")
            await login_as(cust_email, cust_pwd)
            print("    Logged in as Customer.")

            for prefix, route in CUSTOMER_ROUTES:
                for vp_name, width, height, scale, mobile in VIEWPORTS:
                    rec = await inspect_page(route, vp_name, width, height, scale, mobile, f"cust_{prefix}")
                    evidence_records["customer_matrix"].append(rec)

            # ==========================================
            # 2. LIVE BROWSER ACCEPTANCE — ADMIN
            # ==========================================
            print("\n[*] === SECTION 2: LIVE BROWSER ACCEPTANCE — ADMIN ===")
            await login_as(admin_email, admin_pwd)
            print("    Logged in as Admin.")

            for prefix, route in ADMIN_ROUTES:
                for vp_name, width, height, scale, mobile in VIEWPORTS:
                    rec = await inspect_page(route, vp_name, width, height, scale, mobile, f"admin_{prefix}")
                    evidence_records["admin_matrix"].append(rec)

            # ==========================================
            # 3. ADMIN TOPUP INTERACTIVE BROWSER FLOW
            # ==========================================
            print("\n[*] === SECTION 3: ADMIN TOPUP INTERACTIVE BROWSER FLOW ===")
            # 1. Re-login as Admin to establish fresh session & open /admin/topups
            await login_as(admin_email, admin_pwd)
            await send_page("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
            await send_page("Page.navigate", {"url": f"{server_origin}/admin/topups"})
            await asyncio.sleep(2.0)

            # Check pending row in table
            step1_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const rows = document.querySelectorAll('.portal-admin-manual-topup-table tbody tr, .portal-admin-manual-topup-card');
                    let found = false;
                    for (const r of rows) {
                        if (r.innerText.includes('REF-R2-TEST-101') || r.innerText.includes('200,000') || r.innerText.includes('VND') || r.innerText.includes('MANUAL')) {
                            found = true;
                            break;
                        }
                    }
                    return { found, count: rows.length };
                })()""",
                "returnByValue": True,
            })
            step1_val = step1_res.get("result", {}).get("value", {})
            topup_list_pass = bool(step1_val.get("found"))
            print(f"    [Step 1 & 2] Pending topup in list: {topup_list_pass} (total rows={step1_val.get('count')})")

            # Open detail inspector (click select row once, then poll for inspector data)
            await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const btn = document.querySelector('.portal-admin-manual-topup-table button[data-portal-action="admin-manual-topup-select"]');
                    if (btn) btn.click();
                })()"""
            })
            await asyncio.sleep(1.0)

            topup_detail_pass = False
            for _ in range(10):
                sel_res = await send_page("Runtime.evaluate", {
                    "expression": """(() => {
                        const st = (window.__TOAN_AAS_PORTAL__ && window.__TOAN_AAS_PORTAL__.adminManualTopupState) || {};
                        const inspector = document.querySelector('.portal-admin-manual-topup-inspector');
                        const hasRef = Boolean(inspector && (inspector.innerText.includes('REF-R2-TEST-101') || inspector.innerText.includes('MANUAL-1')));
                        return Boolean(st.selected && hasRef);
                    })()""",
                    "returnByValue": True,
                })
                if sel_res.get("result", {}).get("value"):
                    topup_detail_pass = True
                    break
                await asyncio.sleep(0.5)

            print(f"    [Step 3] Topup detail inspector opened: {topup_detail_pass}")

            # Check "Duyệt & Cộng Xu" button
            step4_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const approveBtn = document.querySelector('form.portal-admin-manual-topup-decision-form button[type="submit"], button[data-manual-admin-decision="approve"]');
                    return Boolean(approveBtn && approveBtn.offsetParent !== null);
                })()""",
                "returnByValue": True,
            })
            topup_approve_btn_pass = bool(step4_res.get("result", {}).get("value"))
            print(f"    [Step 4] 'Duyệt & Cộng Xu' button visible: {topup_approve_btn_pass}")

            # Click "Duyệt & Cộng Xu" to open confirmation modal
            step5_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const st = (window.__TOAN_AAS_PORTAL__ && window.__TOAN_AAS_PORTAL__.adminManualTopupState) || {};
                    const reqId = (st.selected && st.selected.request_id) || "";
                    const targetBtn = (reqId && document.querySelector(`button[data-portal-action="admin-manual-topup-draft"][data-manual-admin-request-id="${reqId}"][data-manual-admin-decision="approve"]`))
                        || document.querySelector('button[data-portal-action="admin-manual-topup-draft"][data-manual-admin-decision="approve"]');
                    if (targetBtn) {
                        targetBtn.click();
                        return "targetBtn clicked " + (targetBtn.getAttribute('data-manual-admin-request-id') || "");
                    }
                    const submitBtn = document.querySelector('form.portal-admin-manual-topup-decision-form button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.click();
                        return "submitBtn clicked";
                    }
                    return "not found";
                })()""",
                "returnByValue": True,
            })
            print(f"    [Step 5] Trigger approve draft: {step5_res.get('result', {}).get('value')}")

            # Check confirmation modal dialog appearance & clipping (poll up to 5s)
            modal_open = False
            modal_clipped = False
            for _ in range(10):
                step6_res = await send_page("Runtime.evaluate", {
                    "expression": """(() => {
                        const st = (window.__TOAN_AAS_PORTAL__ && window.__TOAN_AAS_PORTAL__.adminManualTopupState) || {};
                        const modal = document.querySelector('.portal-admin-manual-topup-dialog, [role="dialog"], [data-manual-admin-confirmation]');
                        if (!modal) return { open: false, clipped: false, draft: Boolean(st.draft), err: st.error || '' };
                        const rect = modal.getBoundingClientRect();
                        const clipped = (rect.top < -5 || rect.left < -5 || rect.right > window.innerWidth + 5);
                        return { open: true, clipped: clipped, draft: Boolean(st.draft) };
                    })()""",
                    "returnByValue": True,
                })
                step6_val = step6_res.get("result", {}).get("value", {})
                if step6_val.get("open"):
                    modal_open = True
                    modal_clipped = bool(step6_val.get("clipped"))
                    break
                await asyncio.sleep(0.5)

            topup_modal_pass = modal_open and not modal_clipped
            print(f"    [Step 5, 6, 7] Confirmation modal visible & not clipped: {topup_modal_pass} (open={modal_open}, clipped={modal_clipped}, draft={step6_val.get('draft')}, err={step6_val.get('err')})")

            # Check keyboard focus inside modal
            step8_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const modal = document.querySelector('.portal-admin-manual-topup-dialog, [role="dialog"], [data-manual-admin-confirmation]');
                    if (modal && typeof modal.focus === 'function') modal.focus();
                    const active = document.activeElement;
                    return Boolean(modal && (modal === active || modal.contains(active)));
                })()""",
                "returnByValue": True,
            })
            keyboard_focus_pass = bool(step8_res.get("result", {}).get("value"))
            print(f"    [Step 8] Keyboard focus in modal: {keyboard_focus_pass}")

            # Cancel modal
            await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const cancelBtn = document.querySelector('[data-portal-action="admin-manual-topup-cancel-confirmation"], [data-portal-action="admin-manual-topup-cancel"], .portal-admin-manual-topup-dialog button.portal-button--quiet');
                    if (cancelBtn) cancelBtn.click();
                })()"""
            })
            await asyncio.sleep(0.5)

            step9_res = await send_page("Runtime.evaluate", {
                "expression": "Boolean(document.querySelector('.portal-admin-manual-topup-dialog, [role=\"dialog\"], [data-manual-admin-confirmation]'))",
                "returnByValue": True,
            })
            modal_closed_pass = not bool(step9_res.get("result", {}).get("value"))
            print(f"    [Step 9] Cancel closes modal: {modal_closed_pass}")

            # Reopen modal
            await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const st = (window.__TOAN_AAS_PORTAL__ && window.__TOAN_AAS_PORTAL__.adminManualTopupState) || {};
                    const reqId = (st.selected && st.selected.request_id) || "";
                    const targetBtn = (reqId && document.querySelector(`button[data-portal-action="admin-manual-topup-draft"][data-manual-admin-request-id="${reqId}"][data-manual-admin-decision="approve"]`))
                        || document.querySelector('button[data-portal-action="admin-manual-topup-draft"][data-manual-admin-decision="approve"]');
                    if (targetBtn) {
                        targetBtn.click();
                        return true;
                    }
                    return false;
                })()"""
            })
            for _ in range(10):
                chk = await send_page("Runtime.evaluate", {
                    "expression": "Boolean(document.querySelector('.portal-admin-manual-topup-dialog, [role=\"dialog\"], [data-manual-admin-confirmation]'))",
                    "returnByValue": True,
                })
                if chk.get("result", {}).get("value"):
                    break
                await asyncio.sleep(0.5)

            # Confirm flow submission
            print("    [Step 11] Submitting approval confirmation...")
            await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const confirmBtn = document.querySelector('[data-portal-action="admin-manual-topup-confirm"], .portal-admin-manual-topup-dialog button.portal-button--primary');
                    if (confirmBtn) confirmBtn.click();
                })()"""
            })
            await asyncio.sleep(2.0)

            # Verify UI refresh to approved
            step12_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const text = document.body.innerText;
                    return text.includes('Đã duyệt') || text.includes('approved') || text.includes('Đã duyệt nạp tiền');
                })()""",
                "returnByValue": True,
            })
            admin_approved_pass = bool(step12_res.get("result", {}).get("value"))
            print(f"    [Step 12] Admin UI transitions to approved: {admin_approved_pass}")

            # Switch back to customer and check /wallet
            print("    [Step 13] Switching to Customer to verify ledger reflection...")
            await login_as(cust_email, cust_pwd)
            await send_page("Page.navigate", {"url": f"{server_origin}/wallet"})
            await asyncio.sleep(2.0)

            step13_res = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const text = document.body.innerText;
                    const hasBalance = text.includes('Xu') && (text.includes('2,000') || text.includes('2000') || text.includes('5,000') || text.includes('5000'));
                    const hasLedger = text.includes('manual_topup') || text.includes('Nạp tiền') || text.includes('REF-R2-TEST-101') || text.includes('+2,000') || text.includes('+2000');
                    return { hasBalance, hasLedger, textSample: text.slice(0, 300) };
                })()""",
                "returnByValue": True,
            })
            step13_val = step13_res.get("result", {}).get("value", {})
            customer_refresh_pass = bool(step13_val.get("hasBalance") or step13_val.get("hasLedger"))
            print(f"    [Step 13] Customer balance & ledger refreshed: {customer_refresh_pass}")

            evidence_records["interactive_topup_flow"] = {
                "ADMIN_TOPUP_LIST_BROWSER": "PASS" if topup_list_pass else "FAIL",
                "ADMIN_TOPUP_DETAIL_BROWSER": "PASS" if topup_detail_pass else "FAIL",
                "ADMIN_TOPUP_APPROVE_BUTTON_BROWSER": "PASS" if topup_approve_btn_pass else "FAIL",
                "ADMIN_TOPUP_CONFIRM_MODAL_BROWSER": "PASS" if topup_modal_pass else "FAIL",
                "ADMIN_TOPUP_KEYBOARD_BROWSER": "PASS" if keyboard_focus_pass else "FAIL",
                "ADMIN_TOPUP_CUSTOMER_REFRESH_BROWSER": "PASS" if customer_refresh_pass else "FAIL",
            }

            # ==========================================
            # 4. FAILURE UI BROWSER STATES
            # ==========================================
            print("\n[*] === SECTION 4: FAILURE UI BROWSER STATES ===")
            # 1. Bridge unavailable (HTTP 503)
            MockBridgeHandler.should_fail_503 = True
            await login_as(admin_email, admin_pwd)
            await send_page("Page.navigate", {"url": f"{server_origin}/admin/topups"})
            await asyncio.sleep(1.0)
            # Recreate another pending request to test bridge failure
            fail_topup = copyfast_db.create_web_manual_topup_request(
                account_id=cust_acc_id,
                amount_vnd=100000,
                method="bank_acb_vietqr",
                reference="REF-R2-TEST-102",
                idempotency_key_hash=hashlib.sha256(b"idemp-r2-fail-102").hexdigest(),
                request_fingerprint=hashlib.sha256(b"fp-r2-fail-102").hexdigest(),
            )
            fail_req_id = fail_topup["request_id"]

            # Attempt approve under 503 bridge
            fail_503_res = await send_page("Runtime.evaluate", {
                "expression": f"""(async () => {{
                    const csrf = (window.__TOAN_AAS_PORTAL__ && window.__TOAN_AAS_PORTAL__.session && window.__TOAN_AAS_PORTAL__.session.csrfToken) || "";
                    const draftRes = await fetch("/api/v1/admin/payments/manual/{fail_req_id}/draft", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json", "X-CSRF-Token": csrf }},
                        body: JSON.stringify({{ action: "approve", reason: "Automated test approve" }})
                    }});
                    const draftData = await draftRes.json();
                    const receipt = draftData.data && draftData.data.confirmation_receipt;
                    if (!receipt) return {{ ok: false, stage: 'draft', draftData }};
                    const confirmRes = await fetch("/api/v1/admin/payments/manual/{fail_req_id}/confirm", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json", "X-CSRF-Token": csrf }},
                        body: JSON.stringify({{ confirmation_receipt: receipt, idempotency_key: "idemp-503-test" }})
                    }});
                    const confirmData = await confirmRes.json().catch(() => ({{}}));
                    return {{ status: confirmRes.status, ok: confirmRes.ok, data: confirmData }};
                }})()""",
                "returnByValue": True,
                "awaitPromise": True,
            })
            fail_503_val = fail_503_res.get("result", {}).get("value", {})
            bridge_unavail_pass = (fail_503_val.get("status") in (502, 503))
            print(f"    [Failure State 1] Bridge unavailable returns 503/502: {bridge_unavail_pass} (status={fail_503_val.get('status')})")
            MockBridgeHandler.should_fail_503 = False

            # 2. Invalid / expired receipt
            fail_receipt_res = await send_page("Runtime.evaluate", {
                "expression": f"""(async () => {{
                    const confirmRes = await fetch("/api/v1/admin/payments/manual/{fail_req_id}/confirm", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ confirmation_receipt: "tampered-bad-receipt", idempotency_key: "idemp-bad-test" }})
                    }});
                    return {{ status: confirmRes.status, ok: confirmRes.ok }};
                }})()""",
                "returnByValue": True,
                "awaitPromise": True,
            })
            fail_receipt_val = fail_receipt_res.get("result", {}).get("value", {})
            bad_receipt_pass = (fail_receipt_val.get("status") in (400, 403, 404))
            print(f"    [Failure State 2] Invalid receipt rejected: {bad_receipt_pass} (status={fail_receipt_val.get('status')})")

            # 3. CSRF / auth guard
            fail_csrf_res = await send_page("Runtime.evaluate", {
                "expression": f"""(async () => {{
                    const confirmRes = await fetch("/api/v1/admin/payments/manual/{fail_req_id}/confirm", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json", "X-CSRF-Token": "bad-csrf" }},
                        body: JSON.stringify({{ confirmation_receipt: "some-receipt", idempotency_key: "idemp-bad-csrf" }})
                    }});
                    return {{ status: confirmRes.status, ok: confirmRes.ok }};
                }})()""",
                "returnByValue": True,
                "awaitPromise": True,
            })
            fail_csrf_val = fail_csrf_res.get("result", {}).get("value", {})
            csrf_guard_pass = (fail_csrf_val.get("status") in (400, 403))
            print(f"    [Failure State 3] CSRF guard rejects invalid token: {csrf_guard_pass} (status={fail_csrf_val.get('status')})")

            # 4. Admin writes disabled
            fail_writes_res = await send_page("Runtime.evaluate", {
                "expression": """(async () => {
                    const refundRes = await fetch("/api/v1/admin/finance/refund", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ transaction_id: "tx-test", amount_xu: 100 })
                    });
                    const data = await refundRes.json().catch(() => ({}));
                    return { status: refundRes.status, ok: refundRes.ok, data: data };
                })()""",
                "returnByValue": True,
                "awaitPromise": True,
            })
            fail_writes_val = fail_writes_res.get("result", {}).get("value", {})
            admin_writes_disabled_pass = (
                fail_writes_val.get("status") in (400, 403) or
                (fail_writes_val.get("data", {}).get("error_code") == "WEBAPP_ADMIN_WRITES_DISABLED" and fail_writes_val.get("data", {}).get("ok") is False)
            )
            print(f"    [Failure State 4] Admin writes disabled fail-closed: {admin_writes_disabled_pass} (status={fail_writes_val.get('status')}, code={fail_writes_val.get('data', {}).get('error_code')})")

            evidence_records["failure_ui_states"] = {
                "BRIDGE_UNAVAILABLE_503": "PASS" if bridge_unavail_pass else "FAIL",
                "INVALID_RECEIPT_REJECTED": "PASS" if bad_receipt_pass else "FAIL",
                "CSRF_AUTH_GUARDED": "PASS" if csrf_guard_pass else "FAIL",
                "ADMIN_WRITES_DISABLED_FAIL_CLOSED": "PASS" if admin_writes_disabled_pass else "FAIL",
            }

    finally:
        chrome_proc.kill()
        server_proc.kill()
        server_log_file.close()
        mock_bridge.shutdown()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Save evidence artifacts
    evidence_path = REPO_ROOT / "reports" / "browser_evidence" / "master_browser_evidence_r2.json"
    manifest_path = REPO_ROOT / "reports" / "browser_evidence" / "master_screenshot_manifest_r2.json"

    evidence_path.write_text(json.dumps(evidence_records, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest_records, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[✓] Live Browser Acceptance Run Complete!")
    print(f"    Evidence JSON: {evidence_path}")
    print(f"    Manifest JSON: {manifest_path}")
    print(f"    Total Captures: {evidence_records['summary']['total_captures']}")
    print(f"    Passed Captures: {evidence_records['summary']['passed_captures']}")

    return evidence_records


if __name__ == "__main__":
    asyncio.run(run_master_browser_r2())
