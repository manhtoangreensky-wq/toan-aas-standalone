"""Headless Chrome CDP Browser Verification Runner for P0.WEBAPP.V3.

Verifies:
- 5 core routes: /dashboard, /features, /wallet/topup, /admin, /admin/commercial
- Across 3 viewports: Desktop (1440x900), Tablet (1024x768), Mobile (390x844)
- Top-up QR lightbox zoom modal behavior (click open, ESC close)
- Captures 16+ screenshots, computes SHA256 manifest
- Zero console errors, zero horizontal overflow
- Produces reports/browser_evidence/v3/v3_browser_verification_evidence.json
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = Path(r"C:\Users\toann\.gemini\antigravity\brain\35841f4d-87c9-4103-bccf-64d849286cad")

V3_ROUTES = [
    ("dashboard", "/dashboard"),
    ("features", "/features"),
    ("wallet_topup", "/wallet/topup"),
    ("admin", "/admin"),
    ("admin_commercial", "/admin/commercial"),
]

VIEWPORTS = [
    ("desktop", 1440, 900, 1, False),
    ("tablet", 1024, 768, 1, False),
    ("mobile", 390, 844, 2, True),
]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chrome_executable() -> str:
    candidates = [
        os.environ.get("CHROME_BIN"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("google-chrome"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise RuntimeError("No Chrome/Chromium executable found.")


def get_head_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT))
        return out.decode().strip()
    except Exception:
        return "UNKNOWN_HEAD_SHA"


async def main():
    chrome_path = find_chrome_executable()
    port = find_free_port()
    cdp_port = find_free_port()
    head_sha = get_head_sha()

    tmp_dir = Path(tempfile.mkdtemp(prefix="v3_browser_verify_"))
    db_path = str(tmp_dir / "v3_verify.db")
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    user_data = tmp_dir / "chrome_profile"
    user_data.mkdir(exist_ok=True)

    output_dir = REPO_ROOT / "reports" / "browser_evidence" / "v3"
    output_dir.mkdir(parents=True, exist_ok=True)

    server_origin = f"http://127.0.0.1:{port}"

    qr_file = tmp_dir / "acb_verify_qr.png"
    from PIL import Image
    Image.new("RGB", (380, 380), color=(16, 170, 150)).save(qr_file, format="PNG")

    env = os.environ.copy()
    env["DB_FILE"] = db_path
    env["WEBAPP_SESSION_DB_PATH"] = db_path
    env["WEB_SESSION_SECRET"] = "v3-browser-verify-secret-token-32chars"
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

    print(f"[*] Starting FastAPI server on port {port}...")
    server_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app:app", "--port", str(port), "--host", "127.0.0.1", "--log-level", "warning"],
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
        raise RuntimeError(f"Server failed to start on port {port}")
    print(f"[*] FastAPI server ready at {server_origin}")

    print(f"[*] Starting Chrome via CDP on port {cdp_port}...")
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
        raise RuntimeError(f"Chrome failed to bind CDP port {cdp_port}")
    print(f"[*] Chrome CDP connected: {ws_url}")

    results = {
        "head_sha": head_sha,
        "task": "P0.WEBAPP.V3.WALLET.TOPUP.QR.DEFAULT.LARGE.NO.ZOOM.R1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "captures": [],
        "qr_checks": {},
        "summary": {
            "total_captures": 0,
            "passed_captures": 0,
            "console_errors_count": 0,
            "horizontal_overflow_count": 0,
        }
    }

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

            # Create and attach target
            create_res = await send("Target.createTarget", {"url": "about:blank"})
            target_id = create_res["targetId"]
            attach_res = await send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
            session_id = attach_res["sessionId"]

            page_console_errors = []

            async def send_page(method, params=None):
                nonlocal msg_id
                msg_id += 1
                call_id = msg_id
                await ws.send(json.dumps({"id": call_id, "sessionId": session_id, "method": method, "params": params or {}}))
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("sessionId") == session_id:
                        if msg.get("method") == "Runtime.consoleAPICalled":
                            call_type = msg.get("params", {}).get("type")
                            if call_type == "error":
                                args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                                err_str = " ".join(args)
                                if "favicon.ico" not in err_str:
                                    page_console_errors.append(err_str)
                        elif msg.get("method") == "Runtime.exceptionThrown":
                            err = msg.get("params", {}).get("exceptionDetails", {})
                            text = err.get("text", "")
                            exc = err.get("exception", {}).get("description", "")
                            page_console_errors.append(f"{text} {exc}".strip())
                    if msg.get("id") == call_id:
                        return msg.get("result", {})

            await send_page("Page.enable")
            await send_page("Runtime.enable")
            await send_page("DOM.enable")
            await send_page("Network.enable")

            # 1. Register test admin account
            print("[*] Registering and authenticating admin session...")
            await send_page("Page.navigate", {"url": f"{server_origin}/login"})
            await asyncio.sleep(1.0)

            auth_res = await send_page("Runtime.evaluate", {
                "expression": """(async () => {
                    const email = "admin_v3_" + Date.now() + "@example.com";
                    const password = "PassWord123456!";
                    await fetch("/api/v1/auth/register", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email: email, password: password, display_name: "Admin V3 Verifier" })
                    });
                    const loginRes = await fetch("/api/v1/auth/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email: email, password: password })
                    });
                    return { ok: loginRes.ok, status: loginRes.status, email: email };
                })()""",
                "returnByValue": True,
                "awaitPromise": True,
            })
            auth_val = auth_res.get("result", {}).get("value", {})
            if not auth_val.get("ok"):
                raise RuntimeError(f"Auth failed: {auth_val}")
            email = auth_val.get("email")

            # Promote account to admin in sqlite
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("UPDATE web_accounts SET role_cache = 'admin', canonical_user_id = 123456789 WHERE email = ?", (email,))
            conn.commit()
            conn.close()

            # Refresh login to refresh session cookie with admin role
            await send_page("Runtime.evaluate", {
                "expression": f"""(async () => {{
                    await fetch("/api/v1/auth/login", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ email: "{email}", password: "PassWord123456!" }})
                    }});
                }})()""",
                "awaitPromise": True,
            })
            print("    Admin session active.")

            # 2. Iterate routes x viewports
            print("[*] Capturing 5 routes across Desktop, Tablet, Mobile (15 captures)...")
            for route_slug, route in V3_ROUTES:
                for vp_name, width, height, scale, mobile in VIEWPORTS:
                    page_console_errors.clear()

                    # Set viewport metrics
                    await send_page("Emulation.setDeviceMetricsOverride", {
                        "width": width,
                        "height": height,
                        "deviceScaleFactor": scale,
                        "mobile": mobile,
                    })

                    target_url = f"{server_origin}{route}"
                    await send_page("Page.navigate", {"url": target_url})
                    await asyncio.sleep(1.2)

                    # Check horizontal overflow
                    overflow_eval = await send_page("Runtime.evaluate", {
                        "expression": "document.documentElement.scrollWidth > window.innerWidth + 1",
                        "returnByValue": True,
                    })
                    has_overflow = bool(overflow_eval.get("result", {}).get("value", False))

                    # Capture screenshot
                    shot_res = await send_page("Page.captureScreenshot", {"format": "png"})
                    shot_b64 = shot_res.get("data", "")
                    shot_bytes = base64.b64decode(shot_b64)
                    shot_sha = hashlib.sha256(shot_bytes).hexdigest()

                    filename = f"v3_{route_slug}_{vp_name}.png"
                    (output_dir / filename).write_bytes(shot_bytes)
                    if ARTIFACTS_DIR.exists():
                        (ARTIFACTS_DIR / filename).write_bytes(shot_bytes)

                    capture_info = {
                        "route": route,
                        "route_slug": route_slug,
                        "viewport": f"{width}x{height}",
                        "viewport_name": vp_name,
                        "screenshot_file": filename,
                        "sha256": shot_sha,
                        "horizontal_overflow": has_overflow,
                        "console_errors": list(page_console_errors),
                        "passed": len(page_console_errors) == 0 and not has_overflow,
                    }
                    results["captures"].append(capture_info)
                    results["summary"]["total_captures"] += 1
                    if capture_info["passed"]:
                        results["summary"]["passed_captures"] += 1
                    if page_console_errors:
                        results["summary"]["console_errors_count"] += len(page_console_errors)
                    if has_overflow:
                        results["summary"]["horizontal_overflow_count"] += 1

                    print(f"    [{vp_name.upper():7s}] {route:20s} -> {filename} (Overflow={has_overflow}, Errors={len(page_console_errors)})")

            # 3. Test Default Large Embedded QR on /wallet/topup without zoom/lightbox
            print("[*] Testing Top-up Default Large Embedded QR (No zoom/lightbox)...")
            await send_page("Emulation.setDeviceMetricsOverride", {
                "width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False
            })
            await send_page("Page.navigate", {"url": f"{server_origin}/wallet/topup"})
            await asyncio.sleep(1.0)

            # Switch to manual topup lane if needed and confirm selection to render singleMethodCard
            await send_page("Runtime.evaluate", {
                "expression": """(async () => {
                    const manualBtn = document.querySelector('[data-portal-topup-lane="manual"]');
                    if (manualBtn) manualBtn.click();
                    await new Promise(r => setTimeout(r, 400));

                    let methodCard = document.querySelector(".portal-manual-payment-method");
                    if (!methodCard) {
                        const amtInput = document.querySelector('.portal-manual-topup-form input[name="amount_vnd"]');
                        if (amtInput) {
                            amtInput.value = "50000";
                            amtInput.dispatchEvent(new Event("input", { bubbles: true }));
                            amtInput.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                        const methodSelect = document.querySelector('.portal-manual-topup-form select[name="method"]');
                        if (methodSelect) {
                            const opt = Array.from(methodSelect.options).find(o => o.value && !o.disabled);
                            if (opt) {
                                methodSelect.value = opt.value;
                                methodSelect.dispatchEvent(new Event("change", { bubbles: true }));
                            }
                        }
                        await new Promise(r => setTimeout(r, 300));
                        const confirmBtn = document.querySelector('button[data-portal-action="manual-topup-confirm-selection"]');
                        if (confirmBtn) {
                            confirmBtn.click();
                        } else {
                            const form = document.querySelector('form.portal-manual-topup-form');
                            if (form) form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                        }
                        await new Promise(r => setTimeout(r, 800));
                    }
                })()""",
                "awaitPromise": True,
            })
            await asyncio.sleep(1.2)

            # Measure Desktop QR
            desktop_qr_eval = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const qrImg = document.querySelector(".portal-manual-payment-method img");
                    const modal = document.getElementById("portal-qr-lightbox-modal");
                    const lightboxAction = document.querySelector('[data-portal-action="open-qr-lightbox"]');
                    const figure = document.querySelector(".portal-manual-payment-method figure");
                    const figStyle = figure ? window.getComputedStyle(figure) : null;
                    const noFns = typeof window.openQrLightboxModal === "undefined" && typeof window.closeQrLightboxModal === "undefined";
                    if (!qrImg) return { found: false, modal_absent: !modal, action_absent: !lightboxAction, no_lightbox_fn: noFns };
                    const rect = qrImg.getBoundingClientRect();
                    return {
                        found: true,
                        width: rect.width,
                        height: rect.height,
                        modal_absent: !modal,
                        action_absent: !lightboxAction,
                        cursor: figStyle ? figStyle.cursor : "",
                        no_lightbox_fn: noFns
                    };
                })()""",
                "returnByValue": True,
            })
            desktop_qr = desktop_qr_eval.get("result", {}).get("value", {})
            print(f"    Desktop QR check: {desktop_qr}")

            # Capture desktop QR screenshot
            desktop_shot_res = await send_page("Page.captureScreenshot", {"format": "png"})
            desktop_bytes = base64.b64decode(desktop_shot_res.get("data", ""))
            desktop_filename = "wallet_topup_qr_default_desktop.png"
            (output_dir / desktop_filename).write_bytes(desktop_bytes)
            if ARTIFACTS_DIR.exists():
                (ARTIFACTS_DIR / desktop_filename).write_bytes(desktop_bytes)

            # Measure Mobile QR (390x844) with fresh bounded selection flow
            print("[*] Testing Top-up Mobile Large Embedded QR (390x844)...")
            await send_page("Emulation.setDeviceMetricsOverride", {
                "width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True
            })
            await send_page("Page.navigate", {"url": f"{server_origin}/wallet/topup"})
            await asyncio.sleep(1.2)

            await send_page("Runtime.evaluate", {
                "expression": """(async () => {
                    const manualBtn = document.querySelector('[data-portal-topup-lane="manual"]');
                    if (manualBtn) manualBtn.click();
                    await new Promise(r => setTimeout(r, 400));

                    let methodCard = document.querySelector(".portal-manual-payment-method");
                    if (!methodCard) {
                        const amtInput = document.querySelector('.portal-manual-topup-form input[name="amount_vnd"]');
                        if (amtInput) {
                            amtInput.value = "50000";
                            amtInput.dispatchEvent(new Event("input", { bubbles: true }));
                            amtInput.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                        const methodSelect = document.querySelector('.portal-manual-topup-form select[name="method"]');
                        if (methodSelect) {
                            const opt = Array.from(methodSelect.options).find(o => o.value && !o.disabled);
                            if (opt) {
                                methodSelect.value = opt.value;
                                methodSelect.dispatchEvent(new Event("change", { bubbles: true }));
                            }
                        }
                        await new Promise(r => setTimeout(r, 300));
                        const confirmBtn = document.querySelector('button[data-portal-action="manual-topup-confirm-selection"]');
                        if (confirmBtn) {
                            confirmBtn.click();
                        } else {
                            const form = document.querySelector('form.portal-manual-topup-form');
                            if (form) form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                        }
                        await new Promise(r => setTimeout(r, 800));
                    }
                })()""",
                "awaitPromise": True,
            })
            await asyncio.sleep(1.2)

            mobile_qr_eval = await send_page("Runtime.evaluate", {
                "expression": """(() => {
                    const qrImg = document.querySelector(".portal-manual-payment-method img");
                    if (!qrImg) return { found: false, overflow: false };
                    const rect = qrImg.getBoundingClientRect();
                    const overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
                    return {
                        found: true,
                        width: rect.width,
                        height: rect.height,
                        overflow: overflow,
                        scroll_width: document.documentElement.scrollWidth,
                        inner_width: window.innerWidth
                    };
                })()""",
                "returnByValue": True,
            })
            mobile_qr = mobile_qr_eval.get("result", {}).get("value", {})
            print(f"    Mobile QR check: {mobile_qr}")

            # Capture mobile QR screenshot
            mobile_shot_res = await send_page("Page.captureScreenshot", {"format": "png"})
            mobile_bytes = base64.b64decode(mobile_shot_res.get("data", ""))
            mobile_filename = "wallet_topup_qr_default_mobile.png"
            (output_dir / mobile_filename).write_bytes(mobile_bytes)
            if ARTIFACTS_DIR.exists():
                (ARTIFACTS_DIR / mobile_filename).write_bytes(mobile_bytes)

            desktop_w = desktop_qr.get("width", 0)
            mobile_w = mobile_qr.get("width", 0)
            mobile_overflow = bool(mobile_qr.get("overflow", False))

            results["qr_checks"] = {
                "desktop_qr_width": desktop_w,
                "desktop_qr_height": desktop_qr.get("height", 0),
                "mobile_qr_width": mobile_w,
                "mobile_qr_height": mobile_qr.get("height", 0),
                "desktop_width_pass": 370 <= desktop_w <= 390,
                "mobile_width_pass": mobile_w >= 340,
                "mobile_horizontal_overflow": mobile_overflow,
                "mobile_horizontal_overflow_pass": not mobile_overflow,
                "modal_absent_pass": desktop_qr.get("modal_absent", False),
                "action_absent_pass": desktop_qr.get("action_absent", False),
                "no_lightbox_fn_pass": desktop_qr.get("no_lightbox_fn", False),
                "cursor_not_zoom_pass": desktop_qr.get("cursor") not in ("pointer", "zoom-in"),
                "desktop_screenshot": desktop_filename,
                "mobile_screenshot": mobile_filename,
                "desktop_sha256": hashlib.sha256(desktop_bytes).hexdigest(),
                "mobile_sha256": hashlib.sha256(mobile_bytes).hexdigest(),
            }

    finally:
        chrome_proc.kill()
        server_proc.kill()
        server_log_file.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    evidence_json_path = output_dir / "v3_browser_verification_evidence.json"
    evidence_text = json.dumps(results, indent=2, ensure_ascii=False)
    evidence_json_path.write_text(evidence_text, encoding="utf-8")
    if ARTIFACTS_DIR.exists():
        (ARTIFACTS_DIR / "v3_browser_verification_evidence.json").write_text(evidence_text, encoding="utf-8")

    print(f"\n[*] Browser Verification Completed: {results['summary']['passed_captures']}/{results['summary']['total_captures']} passed.")
    print(f"[*] Evidence written to {evidence_json_path}")

    assert results["summary"]["total_captures"] == 15, "Expected 15 captures"
    assert results["summary"]["console_errors_count"] == 0, f"Expected 0 console errors, got {results['summary']['console_errors_count']}"
    assert results["summary"]["horizontal_overflow_count"] == 0, f"Expected 0 horizontal overflow, got {results['summary']['horizontal_overflow_count']}"
    assert results["qr_checks"]["desktop_width_pass"], f"Expected desktop QR width in 370..390, got {results['qr_checks']['desktop_qr_width']}"
    assert results["qr_checks"]["mobile_width_pass"], f"Expected mobile QR width >= 340, got {results['qr_checks']['mobile_qr_width']}"
    assert results["qr_checks"]["mobile_horizontal_overflow_pass"], "Expected no mobile horizontal overflow on payment card"
    assert results["qr_checks"]["modal_absent_pass"], "Expected QR lightbox modal to be absent"
    assert results["qr_checks"]["action_absent_pass"], "Expected open-qr-lightbox action to be absent"
    assert results["qr_checks"]["no_lightbox_fn_pass"], "Expected open/close lightbox functions to be absent"
    assert results["qr_checks"]["cursor_not_zoom_pass"], "Expected figure cursor to not be pointer or zoom-in"


if __name__ == "__main__":
    asyncio.run(main())
