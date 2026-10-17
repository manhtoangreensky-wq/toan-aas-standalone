"""Run the isolated authenticated WebApp QA matrix for R217-11.

This runner is deliberately separate from the existing six-hub browser gate.  It
creates a temporary SQLite database, starts the WebApp against that database,
creates one customer and one admin fixture per reviewed locale, and records the
customer/Admin route matrix across locale, theme and viewport combinations.

The runner never points at production, never enables a provider bridge, and never
submits a product, payment, wallet or delivery action.  It records guarded UI
states as evidence instead of treating them as successful output.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from typing import Any

import websockets

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.run_browser_verification import (  # noqa: E402
    find_chrome_executable,
    find_free_port,
    launch_headless_chrome,
)


CUSTOMER_ROUTES = (
    "/welcome",
    "/dashboard",
    "/features",
    "/image/create",
    "/voice/tts",
    "/music",
    "/subdub",
    "/tools/video",
    "/video/create",
    "/workboard",
    "/campaigns",
    "/free-prompt-gallery",
    "/wallet/topup",
)
ADMIN_ROUTES = (
    "/admin",
    "/admin/operations",
    "/admin/payments",
    "/admin/customers",
    "/admin/audit",
    "/admin/support",
)
LOCALES = ("vi", "en", "zh")
THEMES = ("light", "dark")
VIEWPORTS = (
    ("phone-375", 375, 812, 2, True),
    ("phone-390", 390, 844, 2, True),
    ("tablet-768", 768, 1024, 1, False),
    ("desktop-1440", 1440, 900, 1, False),
)
EXPECTED_RECORDS = (len(CUSTOMER_ROUTES) + len(ADMIN_ROUTES)) * len(LOCALES) * len(THEMES) * len(VIEWPORTS)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PROTECTED_PATH = re.compile(r"/(?:provider|wallet|topup|payment|payos|ledger|job|bridge|upload|render|delivery)(?:/|$)", re.I)
def _server_env(tmp_dir: Path, db_path: Path, assets_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "DB_FILE": str(db_path),
            "WEBAPP_SESSION_DB_PATH": str(db_path),
            "WEB_SESSION_SECRET": "r21711-isolated-qa-secret-32chars",
            "WEBAPP_ASSET_VAULT_ENABLED": "true",
            "WEBAPP_ASSET_VAULT_ROOT": str(assets_dir),
            "WEBAPP_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_REPLICA_COUNT": "1",
            "WEBAPP_RATE_LIMIT_DISABLED": "true",
            "WEBAPP_VIDEO_OPERATIONS_ENABLED": "false",
            "WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED": "false",
            "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED": "false",
            "WEBAPP_IMAGE_OPERATIONS_ENABLED": "false",
            "WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED": "false",
            "WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED": "false",
            "WEBAPP_AUTOPILOT_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_NOTIFICATION_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_VIDEO_OPERATIONS_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY": "sqlite_single_replica",
            "WEBAPP_SUBTITLE_ASSET_OPERATIONS_TOPOLOGY": "sqlite_single_replica",
        }
    )
    for key in (
        "CORE_BRIDGE_BASE_URL",
        "CORE_BRIDGE_TOKEN",
        "CORE_BRIDGE_HMAC_SECRET",
        "WEBAPP_LINK_CALLBACK_TOKEN",
        "WEBAPP_LINK_CALLBACK_HMAC_SECRET",
        "PAYOS_CLIENT_ID",
        "PAYOS_API_KEY",
        "PAYOS_CHECKSUM_KEY",
    ):
        env.pop(key, None)
    return env


def _start_server(tmp_dir: Path, db_path: Path, assets_dir: Path, port: int) -> tuple[subprocess.Popen, str, Any]:
    origin = f"http://127.0.0.1:{port}"
    log_path = tmp_dir / "server.log"
    log_file = log_path.open("w", encoding="utf-8")
    python_exe = sys.executable
    venv_python = REPO_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if venv_python.exists():
        python_exe = str(venv_python)
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO_ROOT),
        env=_server_env(tmp_dir, db_path, assets_dir),
        stdout=log_file,
        stderr=log_file,
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{origin}/welcome", timeout=1) as response:
                if response.status == 200:
                    return proc, origin, log_file
        except Exception:
            time.sleep(0.25)
    proc.kill()
    log_file.close()
    detail = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    raise RuntimeError(f"isolated WebApp server did not start: {detail[-4000:]}")


def _set_fixture_locale(db_path: Path, email: str, locale: str, role: str, canonical_id: str | None) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET locale=?, role_cache=?, canonical_user_id=? WHERE email=?",
            (locale, role, canonical_id, email),
        )
        conn.commit()


def _load_json_value(result: dict[str, Any]) -> Any:
    return result.get("result", {}).get("value")


async def run_authenticated_matrix(output_dir: Path, head_sha: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="toanaas_r21711_"))
    db_path = tmp_dir / "r21711-qa.db"
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir()
    port = find_free_port()
    server_proc = None
    server_log = None
    chrome_proc = None
    records: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []

    try:
        server_proc, origin, server_log = _start_server(tmp_dir, db_path, assets_dir, port)
        chrome = launch_headless_chrome(find_chrome_executable(), tmp_dir, max_attempts=2)
        chrome_proc = chrome.proc

        async with websockets.connect(chrome.ws_url, max_size=50 * 1024 * 1024) as ws:
            message_id = 0
            session_id = ""
            event_state: dict[str, Any] = {}

            async def send(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
                nonlocal message_id
                message_id += 1
                call_id = message_id
                await ws.send(json.dumps({"id": call_id, "method": method, "params": params or {}}))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("sessionId") == session_id:
                        _collect_event(message, event_state, origin)
                    if message.get("id") == call_id:
                        return message.get("result", {})

            target = await send("Target.createTarget", {"url": "about:blank"})
            attached = await send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
            session_id = attached["sessionId"]

            async def send_page(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
                nonlocal message_id
                message_id += 1
                call_id = message_id
                await ws.send(json.dumps({"id": call_id, "sessionId": session_id, "method": method, "params": params or {}}))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("sessionId") == session_id:
                        _collect_event(message, event_state, origin)
                    if message.get("id") == call_id:
                        return message.get("result", {})

            for domain in ("Page", "Runtime", "Log", "Network", "Accessibility"):
                await send_page(f"{domain}.enable")
            await send_page(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        window.__r21711_unhandled = [];
                        window.addEventListener('unhandledrejection', e => {
                          const reason = e.reason;
                          window.__r21711_unhandled.push(String(reason && (reason.stack || reason.message) || reason));
                        });
                    """,
                },
            )

            async def evaluate(expression: str, await_promise: bool = False) -> Any:
                result = await send_page(
                    "Runtime.evaluate",
                    {"expression": expression, "returnByValue": True, "awaitPromise": await_promise},
                )
                return _load_json_value(result)

            async def clear_session() -> None:
                await send("Network.clearBrowserCookies")
                await send_page("Storage.clearDataForOrigin", {"origin": origin, "storageTypes": "all"})

            async def create_accounts() -> dict[tuple[str, str], str]:
                accounts: dict[tuple[str, str], str] = {}
                for actor, role in (("customer", "user"), ("admin", "admin")):
                    # canonical_user_id is unique in the isolated schema.  Keep one
                    # canonical-admin fixture and switch its locale between sessions;
                    # customer fixtures remain one account per locale.
                    fixture_locales = LOCALES if actor == "customer" else ("vi",)
                    for locale in fixture_locales:
                        email = f"r21711-{actor}-{locale}@qa.invalid"
                        password = "R21711-Isolated-Password!"
                        await send_page("Page.navigate", {"url": f"{origin}/login?lang={locale}"})
                        await asyncio.sleep(0.15)
                        result = await evaluate(
                            """(async () => {
                                const response = await fetch('/api/v1/auth/register', {
                                  method: 'POST', headers: {'Content-Type': 'application/json'},
                                  body: JSON.stringify(%s)
                                });
                                return {status: response.status, body: await response.json()};
                            })()""" % json.dumps({"email": email, "password": password, "display_name": f"R21711 {actor} {locale}"}),
                            True,
                        )
                        if not isinstance(result, dict) or result.get("status") not in (200, 201):
                            raise RuntimeError(f"QA fixture registration failed for {actor}/{locale}: {result}")
                        canonical_id = "canonical-admin" if actor == "admin" else None
                        _set_fixture_locale(db_path, email, locale, role, canonical_id)
                        if actor == "admin":
                            for admin_locale in LOCALES:
                                accounts[(actor, admin_locale)] = email
                        else:
                            accounts[(actor, locale)] = email
                return accounts

            async def login(actor: str, locale: str, email: str) -> None:
                await clear_session()
                _set_fixture_locale(
                    db_path,
                    email,
                    locale,
                    "admin" if actor == "admin" else "user",
                    "canonical-admin" if actor == "admin" else None,
                )
                await send_page("Page.navigate", {"url": f"{origin}/login?lang={locale}"})
                await asyncio.sleep(0.15)
                result = await evaluate(
                    """(async () => {
                        const response = await fetch('/api/v1/auth/login', {
                          method: 'POST', headers: {'Content-Type': 'application/json'},
                          body: JSON.stringify(%s)
                        });
                        return {status: response.status, body: await response.json()};
                    })()""" % json.dumps({"email": email, "password": "R21711-Isolated-Password!", "admin_portal": actor == "admin"}),
                    True,
                )
                if not isinstance(result, dict) or result.get("status") != 200 or not result.get("body", {}).get("ok"):
                    raise RuntimeError(f"QA fixture login failed for {actor}/{locale}: {result}")

            accounts = await create_accounts()
            for actor, routes in (("customer", CUSTOMER_ROUTES), ("admin", ADMIN_ROUTES)):
                for locale in LOCALES:
                    await login(actor, locale, accounts[(actor, locale)])
                    for route in routes:
                        for theme in THEMES:
                            for viewport_name, width, height, scale, mobile in VIEWPORTS:
                                record, image = await _capture_record(
                                    send_page,
                                    evaluate,
                                    event_state,
                                    origin,
                                    actor,
                                    route,
                                    locale,
                                    theme,
                                    viewport_name,
                                    width,
                                    height,
                                    scale,
                                    mobile,
                                )
                                filename = f"{actor}-{route.strip('/').replace('/', '_') or 'welcome'}-{locale}-{theme}-{viewport_name}.png"
                                image_path = screenshot_dir / filename
                                image_path.write_bytes(image)
                                record["screenshot"] = f"screenshots/{filename}"
                                record["screenshot_sha256"] = hashlib.sha256(image).hexdigest()
                                record["screenshot_bytes"] = len(image)
                                records.append(record)
                                screenshots.append(
                                    {
                                        "actor": actor,
                                        "requested_route": route,
                                        "locale": locale,
                                        "theme_requested": theme,
                                        "viewport": f"{width}x{height}",
                                        "filename": f"screenshots/{filename}",
                                        "file_size": len(image),
                                        "sha256": hashlib.sha256(image).hexdigest(),
                                        "head_sha": head_sha,
                                    }
                                )
                                print(f"[{len(records):03d}/{EXPECTED_RECORDS}] {actor} {locale}/{theme} {viewport_name} {route} -> {record['pass']}")

    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "r21711-authenticated-qa-error.json").write_text(
            json.dumps(
                {
                    "schema": "R217-11-authenticated-qa-error-v1",
                    "head_sha": head_sha,
                    "server_origin": "isolated-local-test-origin",
                    "error": str(exc),
                    "records_completed": len(records),
                    "records_expected": EXPECTED_RECORDS,
                    "provider_calls": 0,
                    "wallet_mutations": 0,
                    "production_data_mutations": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise
    finally:
        if chrome_proc is not None:
            chrome_proc.terminate()
            try:
                chrome_proc.wait(timeout=5)
            except Exception:
                chrome_proc.kill()
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except Exception:
                server_proc.kill()
        if server_log is not None:
            server_log.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    failed = [row for row in records if not row.get("pass")]
    evidence = {
        "schema": "R217-11-authenticated-qa-matrix-v1",
        "head_sha": head_sha,
        "server_origin": "isolated-local-test-origin",
        "records_expected": EXPECTED_RECORDS,
        "records_completed": len(records),
        "records_passed": len(records) - len(failed),
        "records_failed": len(failed),
        "provider_calls": 0,
        "wallet_mutations": 0,
        "production_data_mutations": 0,
        "records": records,
        "screenshot_manifest": screenshots,
        "failure_samples": failed[:20],
    }
    evidence_path = output_dir / "r21711-authenticated-qa-matrix.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "screenshot-manifest.json").write_text(json.dumps(screenshots, ensure_ascii=False, indent=2), encoding="utf-8")

    if len(records) != EXPECTED_RECORDS or failed:
        raise RuntimeError(f"R217-11 matrix failed closed: {len(records)}/{EXPECTED_RECORDS} records, failures={len(failed)}")
    return evidence


def _collect_event(message: dict[str, Any], state: dict[str, Any], origin: str) -> None:
    method = message.get("method")
    params = message.get("params", {})
    if method == "Runtime.exceptionThrown":
        details = params.get("exceptionDetails", {})
        state.setdefault("page_errors", []).append(str(details.get("text") or details.get("exception", {}).get("description") or "exception"))
    elif method == "Runtime.consoleAPICalled":
        kind = params.get("type")
        if kind in ("error", "warning"):
            args = params.get("args", [])
            state.setdefault("console", []).append(
                {"type": kind, "text": " ".join(str(item.get("value", item.get("description", ""))) for item in args)}
            )
    elif method == "Network.requestWillBeSent":
        request = params.get("request", {})
        url = str(request.get("url", ""))
        method_name = str(request.get("method", "GET")).upper()
        request_id = str(params.get("requestId", ""))
        state.setdefault("requests", []).append({"request_id": request_id, "url": url, "method": method_name})
        state.setdefault("request_urls", {})[request_id] = url
        parsed = urllib.parse.urlparse(url)
        origin_parsed = urllib.parse.urlparse(origin)
        if parsed.scheme in ("http", "https") and parsed.netloc != origin_parsed.netloc:
            state.setdefault("external_requests", []).append(url)
        if method_name in MUTATING_METHODS and (parsed.netloc != origin_parsed.netloc or PROTECTED_PATH.search(parsed.path)):
            state.setdefault("forbidden_mutations", []).append({"method": method_name, "url": url})
    elif method == "Network.responseReceived":
        response = params.get("response", {})
        if params.get("type") == "Document":
            state.setdefault("document_statuses", []).append({"url": response.get("url", ""), "status": response.get("status", 0)})
    elif method == "Network.loadingFailed":
        request_id = str(params.get("requestId", ""))
        failed_url = state.setdefault("request_urls", {}).get(request_id, request_id)
        if not str(failed_url).endswith("/favicon.ico"):
            state.setdefault("failed_requests", []).append({"url": failed_url, "error": params.get("errorText", "")})


async def _capture_record(
    send_page: Any,
    evaluate: Any,
    event_state: dict[str, Any],
    origin: str,
    actor: str,
    route: str,
    locale: str,
    theme: str,
    viewport_name: str,
    width: int,
    height: int,
    scale: int,
    mobile: bool,
) -> tuple[dict[str, Any], bytes]:
    event_state.clear()
    url = f"{origin}{route}?lang={locale}&theme={theme}"
    await send_page(
        "Emulation.setDeviceMetricsOverride",
        {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": mobile},
    )
    await send_page("Page.navigate", {"url": url})
    for _ in range(18):
        ready = await evaluate(
            "Boolean(document.readyState === 'complete' && document.querySelector('h1,h2,h3,.portal-title,.portal-card-title'))"
        )
        if ready:
            break
        await asyncio.sleep(0.1)
    dom = await evaluate(
        """(() => {
            const visible = el => { if (!el) return false; const s = getComputedStyle(el), r = el.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0; };
            const name = el => (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 160);
            const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
            const focus = controls.filter(el => el.tabIndex >= 0).map((el, index) => ({index, tag: el.tagName.toLowerCase(), name: name(el), tabIndex: el.tabIndex})).slice(0, 80);
            const fields = [...document.querySelectorAll('input,select,textarea')].filter(visible).map(el => ({tag: el.tagName.toLowerCase(), type: el.getAttribute('type') || '', name: el.getAttribute('name') || '', label: name(el)}));
            const headings = [...document.querySelectorAll('h1,h2,h3')].filter(visible).map(name).slice(0, 12);
            const statusNodes = [...document.querySelectorAll('[data-portal-state],[data-state],[data-status],[aria-live]')].filter(visible).map(el => ({state: el.getAttribute('data-portal-state') || el.getAttribute('data-state') || el.getAttribute('data-status') || '', text: name(el)})).slice(0, 40);
            const main = document.querySelector('main, .portal-page, article.portal-page');
            const mainRect = main ? main.getBoundingClientRect() : null;
            const text = (document.body && document.body.innerText || '').replace(/\\s+/g, ' ');
            return {
                title: document.title,
                resolved_route: location.pathname,
                resolved_url: location.href,
                resolved_locale: document.documentElement.getAttribute('data-portal-locale') || document.documentElement.getAttribute('lang') || '',
                resolved_theme: document.documentElement.getAttribute('data-portal-theme') || '',
                horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
                main_visible: Boolean(main && visible(main) && mainRect && mainRect.width <= window.innerWidth + 8),
                headings,
                heading: headings[0] || '',
                interactive_count: controls.length,
                primary_cta_count: document.querySelectorAll('.portal-button--primary,[data-portal-action="primary"],button[type="submit"]').length,
                fields,
                focus_order: focus,
                status_nodes: statusNodes,
                status_markers: text.match(/(?:guarded|blocked|draft|processing|completed|failed|retry|đang xử lý|hoàn tất|bị chặn|bản nháp|thử lại)/gi) || [],
                unhandled_rejections: window.__r21711_unhandled || []
            };
        })()"""
    )
    ax_result = await send_page("Accessibility.getFullAXTree")
    ax_nodes = []
    for node in ax_result.get("nodes", [])[:120]:
        ax_nodes.append(
            {
                "role": node.get("role", {}).get("value", ""),
                "name": node.get("name", {}).get("value", ""),
                "ignored": bool(node.get("ignored")),
            }
        )
    await send_page("Page.reload")
    for _ in range(12):
        ready = await evaluate(
            "Boolean(document.readyState === 'complete' && document.querySelector('h1,h2,h3,.portal-title,.portal-card-title'))"
        )
        if ready:
            break
        await asyncio.sleep(0.1)
    reload_state = await evaluate(
        "JSON.stringify({locale: document.documentElement.getAttribute('data-portal-locale') || document.documentElement.getAttribute('lang') || '', theme: document.documentElement.getAttribute('data-portal-theme') || '', route: location.pathname})"
    )
    try:
        reload_state = json.loads(reload_state or "{}")
    except (TypeError, json.JSONDecodeError):
        reload_state = {}
    image_result = await send_page("Page.captureScreenshot", {"format": "png"})
    image = base64.b64decode(image_result["data"])
    documents = event_state.get("document_statuses", [])
    http_status = int(documents[-1].get("status", 0)) if documents else 0
    console = event_state.get("console", [])
    expected_theme = "light" if actor == "admin" else theme
    row = {
        "actor": actor,
        "requested_route": route,
        "resolved_route": (dom or {}).get("resolved_route", ""),
        "resolved_url": (dom or {}).get("resolved_url", ""),
        "locale": locale,
        "resolved_locale": (dom or {}).get("resolved_locale", ""),
        "theme_requested": theme,
        "theme_resolved": (dom or {}).get("resolved_theme", ""),
        "viewport": f"{width}x{height}",
        "viewport_name": viewport_name,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "http_status": http_status,
        "title": (dom or {}).get("title", ""),
        "heading": (dom or {}).get("heading", ""),
        "headings": (dom or {}).get("headings", []),
        "interactive_count": (dom or {}).get("interactive_count", 0),
        "primary_cta_count": (dom or {}).get("primary_cta_count", 0),
        "fields": (dom or {}).get("fields", []),
        "ax_nodes": ax_nodes,
        "focus_order": (dom or {}).get("focus_order", []),
        "status_nodes": (dom or {}).get("status_nodes", []),
        "status_markers": (dom or {}).get("status_markers", []),
        "console_errors": [item for item in console if item.get("type") == "error"],
        "console_warnings": [item for item in console if item.get("type") == "warning"],
        "page_errors": event_state.get("page_errors", []),
        "failed_requests": event_state.get("failed_requests", []),
        "external_requests": event_state.get("external_requests", []),
        "forbidden_mutations": event_state.get("forbidden_mutations", []),
        "network_requests": event_state.get("requests", []),
        "reload_persistence": {
            "route": reload_state.get("route", ""),
            "locale": reload_state.get("locale", ""),
            "theme": reload_state.get("theme", ""),
        },
        "guarded_boundary_recorded": bool((dom or {}).get("status_nodes") or (dom or {}).get("status_markers")),
    }
    row["pass"] = bool(
        http_status == 200
        and row["resolved_route"] == route
        and row["resolved_locale"] == locale
        and row["theme_resolved"] == expected_theme
        and bool(row["title"])
        and bool(row["heading"])
        and int(row["interactive_count"]) > 0
        and not bool((dom or {}).get("horizontal_overflow"))
        and not row["console_errors"]
        and not row["console_warnings"]
        and not row["page_errors"]
        and not row["failed_requests"]
        and not row["external_requests"]
        and not row["forbidden_mutations"]
        and row["reload_persistence"]["route"] == route
        and row["reload_persistence"]["locale"] == locale
        and row["reload_persistence"]["theme"] == expected_theme
    )
    return row, image


def main() -> None:
    parser = argparse.ArgumentParser(description="Run R217-11 authenticated WebApp matrix in isolated QA")
    parser.add_argument("--output-dir", default="reports/qa_authenticated")
    parser.add_argument("--head-sha", default=None)
    args = parser.parse_args()
    head_sha = args.head_sha or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    asyncio.run(run_authenticated_matrix(Path(args.output_dir), head_sha))


if __name__ == "__main__":
    main()
